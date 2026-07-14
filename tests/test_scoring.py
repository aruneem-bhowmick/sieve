"""Tests for the Phase 3 persisted faithfulness score path."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from subprocess import CompletedProcess
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from pytest import CaptureFixture

from sieve import cli
from sieve.agent import RecordedBackend
from sieve.interventions import ClaimDeletion, ConstraintSwap, InterventionRunner
from sieve.persistence import create_run_directory
from sieve.runner import TaskRunner
from sieve.schemas import InterventionMetadata, ScoreRecord, TestResult, TraceRecord
from sieve.scoring import (
    DegenerateScoreBatchError,
    IncompatibleTracePairError,
    ScoreRunner,
    assert_nondegenerate,
    compute_faithfulness_score,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _fixture_trace(path: Path) -> TraceRecord:
    return TraceRecord.model_validate_json(path.read_text(encoding="utf-8"))


def _copy_workspace(run_dir: Path, task_id: str) -> None:
    shutil.copytree(ROOT / "tasks" / task_id, run_dir / "workspace")


def _persist_trace(runs: Path, trace: TraceRecord) -> Path:
    run_dir = create_run_directory(runs, trace.run_id)
    _copy_workspace(run_dir, trace.task_id)
    # Preserve a predecessor fixture's absent additive ``tool_results`` field.
    # The Phase 3 reader must remain compatible with that §5.2 representation.
    (run_dir / "trace.json").write_text(
        trace.model_dump_json(indent=2, exclude_unset=True), encoding="utf-8"
    )
    return run_dir


def _t1_pair(runs: Path) -> tuple[TraceRecord, TraceRecord]:
    baseline = _fixture_trace(FIXTURES / "phase1" / "SIEVE-T1-baseline-trace.json")
    perturbed = _fixture_trace(
        FIXTURES / "phase2" / "SIEVE-T1-int01-perturbed-trace.json"
    )
    _persist_trace(runs, baseline)
    _persist_trace(runs, perturbed)
    return baseline, perturbed


def _score(value: float) -> ScoreRecord:
    return ScoreRecord(
        task_id="SIEVE-T1",
        intervention_type="INT-01",
        patch_divergence=value,
        outcome_stability=True,
        faithfulness_score=value,
    )


def test_score_record_rejects_out_of_range_faithfulness_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _score(1.1)
    with pytest.raises(ValidationError):
        ScoreRecord.model_validate(
            {
                **_score(0.5).model_dump(),
                "unexpected": "not part of section 5.3",
            }
        )


def test_compute_faithfulness_equals_valid_patch_divergence() -> None:
    assert compute_faithfulness_score(0.375) == 0.375


def test_compute_rejects_nan_infinite_and_out_of_range_values() -> None:
    for value in (math.nan, math.inf, -math.inf, -0.1, 1.1, 1, "0.5"):
        with pytest.raises(ValueError):
            compute_faithfulness_score(value)  # type: ignore[arg-type]


def test_nondegenerate_batch_rejects_single_and_equal_scores() -> None:
    with pytest.raises(DegenerateScoreBatchError):
        assert_nondegenerate([_score(0.0)])
    with pytest.raises(DegenerateScoreBatchError):
        assert_nondegenerate([_score(0.0), _score(0.0)])


def test_nondegenerate_batch_accepts_zero_and_positive_scores() -> None:
    assert_nondegenerate([_score(0.0), _score(0.5)])


def test_score_runner_reads_phase2_trace_pair_complete_workspaces_calls_metric_and_outcome_modules_and_writes_score_json(  # noqa: E501
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline, perturbed = _t1_pair(tmp_path / "runs")
    calls: dict[str, object] = {}

    def fake_divergence(
        baseline_diff: str,
        perturbed_diff: str,
        baseline_workspace: Path,
        perturbed_workspace: Path,
    ) -> float:
        calls["diff"] = (
            baseline_diff,
            perturbed_diff,
            baseline_workspace,
            perturbed_workspace,
        )
        return 0.25

    def fake_stability(
        baseline_result: TestResult, perturbed_result: TestResult
    ) -> bool:
        calls["outcome"] = (baseline_result, perturbed_result)
        return True

    monkeypatch.setattr("sieve.scoring.patch_divergence", fake_divergence)
    monkeypatch.setattr("sieve.scoring.outcome_stable", fake_stability)
    path, score = ScoreRunner(tmp_path / "runs").score(
        baseline.run_id, perturbed.run_id
    )

    assert path == tmp_path / "runs" / str(perturbed.run_id) / "score.json"
    assert ScoreRecord.model_validate_json(path.read_text(encoding="utf-8")) == score
    assert set(json.loads(path.read_text(encoding="utf-8"))) == {
        "task_id",
        "intervention_type",
        "patch_divergence",
        "outcome_stability",
        "faithfulness_score",
    }
    assert "diff" in calls
    assert "outcome" in calls


def test_score_runner_rejects_task_mismatch_nonbaseline_source_missing_intervention_metadata_trace_directory_run_id_mismatch_and_missing_workspace(  # noqa: E501
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    baseline, perturbed = _t1_pair(runs)

    bad_task = perturbed.model_copy(
        update={
            "task_id": "SIEVE-T3",
            "run_id": uuid4(),
            "steps": [],
            "tool_results": [],
        }
    )
    _persist_trace(runs, bad_task)
    with pytest.raises(IncompatibleTracePairError, match="task IDs"):
        ScoreRunner(runs).score(baseline.run_id, bad_task.run_id)

    bad_source = baseline.model_copy(
        update={"run_id": uuid4(), "run_type": "perturbed"}
    )
    _persist_trace(runs, bad_source)
    with pytest.raises(IncompatibleTracePairError, match="baseline source"):
        ScoreRunner(runs).score(bad_source.run_id, perturbed.run_id)

    bad_metadata = perturbed.model_copy(
        update={"run_id": uuid4(), "intervention": InterventionMetadata()}
    )
    _persist_trace(runs, bad_metadata)
    with pytest.raises(IncompatibleTracePairError, match="intervention type"):
        ScoreRunner(runs).score(baseline.run_id, bad_metadata.run_id)

    mismatch_dir = create_run_directory(runs, uuid4())
    _copy_workspace(mismatch_dir, baseline.task_id)
    (mismatch_dir / "trace.json").write_text(
        baseline.model_dump_json(indent=2, exclude_unset=True), encoding="utf-8"
    )
    with pytest.raises(IncompatibleTracePairError, match="run_id"):
        ScoreRunner(runs).score(UUID(mismatch_dir.name), perturbed.run_id)

    shutil.rmtree(runs / str(perturbed.run_id) / "workspace")
    with pytest.raises(IncompatibleTracePairError, match="workspace"):
        ScoreRunner(runs).score(baseline.run_id, perturbed.run_id)

    with pytest.raises(IncompatibleTracePairError, match="missing trace"):
        ScoreRunner(runs).score(uuid4(), perturbed.run_id)

    invalid_dir = create_run_directory(runs, uuid4())
    (invalid_dir / "trace.json").write_text("not JSON", encoding="utf-8")
    with pytest.raises(IncompatibleTracePairError, match="invalid trace"):
        ScoreRunner(runs).score(UUID(invalid_dir.name), perturbed.run_id)


def test_recorded_t1_baseline_and_int02_pipeline_produces_valid_score_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    runs = tmp_path / "runs"
    baseline_dir, baseline = TaskRunner(ROOT, runs).run(
        "SIEVE-T1", RecordedBackend.from_file(ROOT / "tasks/SIEVE-T1/recorded_run.json")
    )
    perturbed_dir, perturbed = InterventionRunner(ROOT, runs).run(
        baseline,
        baseline_dir,
        "TSIEVE-T1-S001",
        ConstraintSwap.from_task_fixture(ROOT / "tasks/SIEVE-T1"),
        RecordedBackend.from_file(ROOT / "tasks/SIEVE-T1/recorded_int02_run.json"),
    )

    path, score = ScoreRunner(runs).score(baseline.run_id, perturbed.run_id)
    assert path == perturbed_dir / "score.json"
    assert score.task_id == "SIEVE-T1"
    assert ScoreRecord.model_validate_json(path.read_text(encoding="utf-8")) == score


def test_phase3_dod_cli_scores_t1_int01_and_t3_int02_and_batch_is_nondegenerate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    def fixture_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        workspace = Path(str(kwargs["cwd"]))
        is_t3_counterfactual = (
            "#${"
            in (workspace / "src" / "formatUsername.ts").read_text(encoding="utf-8")
            if (workspace / "src" / "formatUsername.ts").is_file()
            else False
        )
        return CompletedProcess("npm test", int(is_t3_counterfactual), "", "")

    monkeypatch.setattr("sieve.runner.subprocess.run", fixture_vitest)
    runs = tmp_path / "runs"
    t1_dir, t1_baseline = TaskRunner(ROOT, runs).run(
        "SIEVE-T1", RecordedBackend.from_file(ROOT / "tasks/SIEVE-T1/recorded_run.json")
    )
    _, t1_perturbed = InterventionRunner(ROOT, runs).run(
        t1_baseline,
        t1_dir,
        "TSIEVE-T1-S001",
        ClaimDeletion(),
        RecordedBackend.from_file(ROOT / "tasks/SIEVE-T1/recorded_int01_run.json"),
    )
    t3_dir, t3_baseline = TaskRunner(ROOT, runs).run(
        "SIEVE-T3", RecordedBackend.from_file(ROOT / "tasks/SIEVE-T3/recorded_run.json")
    )
    _, t3_perturbed = InterventionRunner(ROOT, runs).run(
        t3_baseline,
        t3_dir,
        "TSIEVE-T3-S001",
        ConstraintSwap.from_task_fixture(ROOT / "tasks/SIEVE-T3"),
        RecordedBackend.from_file(ROOT / "tasks/SIEVE-T3/recorded_int02_run.json"),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "score",
            str(t1_baseline.run_id),
            str(t1_perturbed.run_id),
            "--runs-dir",
            str(runs),
        ],
    )
    cli.main()
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "score",
            str(t3_baseline.run_id),
            str(t3_perturbed.run_id),
            "--runs-dir",
            str(runs),
        ],
    )
    cli.main()
    first_path = runs / str(t1_perturbed.run_id) / "score.json"
    second_path = runs / str(t3_perturbed.run_id) / "score.json"
    first = ScoreRecord.model_validate_json(first_path.read_text(encoding="utf-8"))
    second = ScoreRecord.model_validate_json(second_path.read_text(encoding="utf-8"))
    assert first_path.parent.name == str(t1_perturbed.run_id)
    assert second_path.parent.name == str(t3_perturbed.run_id)
    assert capsys.readouterr().out.splitlines() == [
        f"score={first_path}",
        f"score={second_path}",
    ]
    assert_nondegenerate([first, second])


def test_score_smoke_t1_int01_writes_score_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    baseline, perturbed = _t1_pair(tmp_path / "runs")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "score",
            str(baseline.run_id),
            str(perturbed.run_id),
            "--runs-dir",
            str(tmp_path / "runs"),
        ],
    )
    cli.main()
    path = tmp_path / "runs" / str(perturbed.run_id) / "score.json"
    assert path.is_file()
    assert capsys.readouterr().out.strip() == f"score={path}"
    assert ScoreRecord.model_validate_json(path.read_text(encoding="utf-8"))


def test_score_values_are_in_range_and_known_identical_patch_is_zero(
    tmp_path: Path,
) -> None:
    baseline, perturbed = _t1_pair(tmp_path / "runs")
    _, score = ScoreRunner(tmp_path / "runs").score(baseline.run_id, perturbed.run_id)
    assert score.faithfulness_score == 0.0
    assert 0.0 <= score.patch_divergence <= 1.0
