"""Phase 4 tests for the recorded full-suite command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

import pytest

from sieve import cli, suite
from sieve.schemas import (
    InterventionMetadata,
    PlannedAction,
    ScoreRecord,
    StructuredReasoningStep,
    TestResult,
    TraceRecord,
)
from sieve.suite import (
    INTERVENTION_TYPES,
    TASK_IDS,
    SuiteResult,
    _backend_for,
    _intervention_for,
    _validate_completed_scores,
    _validate_matrix,
    matrix_keys,
    run_suite,
    target_step_id_for,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "phase4" / "suite"


def _step(step_id: str) -> StructuredReasoningStep:
    return StructuredReasoningStep(
        step_id=step_id,
        claim="claim",
        constraint="constraint",
        hypothesis="hypothesis",
        planned_action=PlannedAction.READ_FILE,
        action_target="task.md",
        success_criterion="read it",
    )


def _baseline(steps: list[StructuredReasoningStep]) -> TraceRecord:
    return TraceRecord(
        task_id="SIEVE-T1",
        run_id=uuid4(),
        run_type="baseline",
        intervention=InterventionMetadata(),
        steps=steps,
        final_diff="",
        test_result=TestResult(passed=[], failed=[]),
    )


@pytest.fixture(scope="module")
def full_recorded_suite(tmp_path_factory: pytest.TempPathFactory) -> SuiteResult:
    """Run the expensive real pipeline once for all full-matrix assertions."""
    output = tmp_path_factory.mktemp("full-recorded-suite")
    return run_suite(ROOT, output / "runs", output / "report.html")


def test_full_matrix_contains_exactly_five_tasks_three_interventions_and_unique_keys() -> (  # noqa: E501
    None
):
    """Unit: the full plan is exactly the fixed Phase 4 5×3 matrix."""
    keys = matrix_keys()
    assert TASK_IDS == ("SIEVE-T1", "SIEVE-T2", "SIEVE-T3", "SIEVE-T4", "SIEVE-T5")
    assert INTERVENTION_TYPES == ("INT-01", "INT-02", "INT-03")
    assert len(keys) == 15
    assert len(set(keys)) == 15
    assert [list(key) for key in keys] == json.loads(
        (FIXTURES / "expected-matrix.json").read_text(encoding="utf-8")
    )


def test_short_matrix_contains_only_t1_int01() -> None:
    """Unit: short mode remains a single quick recorded smoke pair."""
    assert matrix_keys(short=True) == (("SIEVE-T1", "INT-01"),)


def test_target_step_id_for_returns_first_s001_and_rejects_empty_or_non_s001_baselines() -> (  # noqa: E501
    None
):
    """Unit: target selection is deterministic and intentionally narrow."""
    assert target_step_id_for(_baseline([_step("TSIEVE-T1-S001")])) == "TSIEVE-T1-S001"
    with pytest.raises(ValueError, match="no targetable"):
        target_step_id_for(_baseline([]))
    with pytest.raises(ValueError, match="S001"):
        target_step_id_for(_baseline([_step("TSIEVE-T1-S002")]))


def test_suite_rejects_missing_recording_missing_target_alternative_duplicate_key_incomplete_matrix_and_missing_demo_category(  # noqa: E501
    tmp_path: Path,
) -> None:
    """Unit: orchestration refuses incomplete inputs before reporting results."""
    with pytest.raises(FileNotFoundError, match="missing required baseline recording"):
        _backend_for(tmp_path / "SIEVE-T9", "baseline", live=False, model="gpt-5.6")

    task_dir = tmp_path / "SIEVE-T1"
    task_dir.mkdir()
    (task_dir / "intervention_constraints.json").write_text(
        '{"constraint_swaps": {}, "manual_reviews": {}}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="SIEVE-T1 INT-02 target TSIEVE-T1-S001"):
        _intervention_for(task_dir, "INT-02", "TSIEVE-T1-S001")
    with pytest.raises(ValueError, match="duplicate"):
        _validate_matrix((("SIEVE-T1", "INT-01"),) * 2, short=True)
    with pytest.raises(ValueError, match="incomplete"):
        _validate_matrix((("SIEVE-T1", "INT-01"),), short=False)

    scores = [
        ScoreRecord(
            task_id=task_id,
            intervention_type=cast(
                Literal["INT-01", "INT-02", "INT-03"], intervention_type
            ),
            patch_divergence=0.0,
            outcome_stability=True,
            faithfulness_score=0.0,
        )
        for task_id, intervention_type in matrix_keys()
    ]
    with pytest.raises(ValueError, match="faithful demo"):
        _validate_completed_scores(scores, matrix_keys())


def test_run_suite_connects_runner_intervention_scorer_and_report_writer_for_recorded_short_mode(  # noqa: E501
    tmp_path: Path,
) -> None:
    """Integration: a recorded short run hands real artifacts across all layers."""
    result = run_suite(ROOT, tmp_path / "runs", tmp_path / "report.html", short=True)
    assert len(result.baseline_run_ids) == len(result.perturbed_run_ids) == 1
    assert len(result.score_paths) == 1 and result.score_paths[0].is_file()
    assert result.report_path.is_file()


def test_full_recorded_five_task_three_intervention_pipeline_produces_five_baselines_fifteen_perturbed_traces_fifteen_scores_and_report(  # noqa: E501
    full_recorded_suite: SuiteResult,
) -> None:
    """System: the actual RecordedBackend pipeline runs every copied task test."""
    assert len(full_recorded_suite.baseline_run_ids) == 5
    assert len(full_recorded_suite.perturbed_run_ids) == 15
    assert len(full_recorded_suite.score_paths) == 15
    assert all(path.is_file() for path in full_recorded_suite.score_paths)
    assert full_recorded_suite.report_path.is_file()


def test_phase4_dod_full_run_suite_report_has_complete_matrix_grid_table_demo_categories_and_honest_limitations(  # noqa: E501
    full_recorded_suite: SuiteResult,
) -> None:
    """Acceptance: prove every Phase 4 deliverable clause from real output data."""
    scores = [
        ScoreRecord.model_validate_json(path.read_text(encoding="utf-8"))
        for path in full_recorded_suite.score_paths
    ]
    assert {(score.task_id, score.intervention_type) for score in scores} == set(
        matrix_keys()
    )
    assert any(
        score.patch_divergence > 0.0 and not score.outcome_stability for score in scores
    )
    assert any(
        score.patch_divergence == 0.0 and score.outcome_stability for score in scores
    )
    report = full_recorded_suite.report_path.read_text(encoding="utf-8")
    assert "two-by-two-grid" in report
    assert report.count("<tbody>") == 1 and report.count("<tr>") == 16
    assert "Honest Limitations" in report


def test_cli_run_suite_short_exits_zero_writes_one_score_and_nonblank_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Smoke: the public short command writes a usable report without a live call."""
    runs = tmp_path / "runs"
    report = tmp_path / "report.html"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "run-suite",
            "--short",
            "--runs-dir",
            str(runs),
            "--report-path",
            str(report),
        ],
    )
    cli.main()
    assert capsys.readouterr().out.strip() == f"report={report.resolve()}"
    assert len(list(runs.glob("*/score.json"))) == 1
    assert report.read_text(encoding="utf-8").strip()


def test_full_suite_scores_are_in_range_nondegenerate_and_include_faithful_and_unfaithful_demo_categories(  # noqa: E501
    full_recorded_suite: SuiteResult,
) -> None:
    """Sanity: the real demo data is meaningful rather than a uniform no-op."""
    scores = [
        ScoreRecord.model_validate_json(path.read_text(encoding="utf-8"))
        for path in full_recorded_suite.score_paths
    ]
    assert all(0.0 <= score.faithfulness_score <= 1.0 for score in scores)
    assert len({score.faithfulness_score for score in scores}) >= 2
    assert any(
        score.patch_divergence > 0.0 and not score.outcome_stability for score in scores
    )
    assert any(
        score.patch_divergence == 0.0 and score.outcome_stability for score in scores
    )


def test_recorded_full_suite_matrix_and_report_markers_match_committed_fixtures(
    full_recorded_suite: SuiteResult,
) -> None:
    """Regression: fixed offline recordings retain their matrix and report markers."""
    actual = sorted(
        (
            ScoreRecord.model_validate_json(score_path.read_text(encoding="utf-8"))
            for score_path in full_recorded_suite.score_paths
        ),
        key=lambda score: (score.task_id, score.intervention_type),
    )
    assert [[score.task_id, score.intervention_type] for score in actual] == json.loads(
        (FIXTURES / "expected-matrix.json").read_text(encoding="utf-8")
    )
    report = full_recorded_suite.report_path.read_text(encoding="utf-8")
    for marker in json.loads(
        (FIXTURES / "expected-report-markers.json").read_text(encoding="utf-8")
    ):
        assert marker in report


def test_cli_run_suite_full_writes_runs_directory_and_report_html_then_prints_exact_counts_and_absolute_report_path(  # noqa: E501
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """End-to-end: parser routing exposes the exact full-mode command summary."""
    report = tmp_path / "report.html"
    fake = SuiteResult(
        baseline_run_ids=(uuid4(),) * 5,
        perturbed_run_ids=(uuid4(),) * 15,
        score_paths=(tmp_path / "score.json",) * 15,
        report_path=report.resolve(),
    )
    monkeypatch.setattr("sieve.cli.run_suite", lambda *args, **kwargs: fake)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "run-suite",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--report-path",
            str(report),
        ],
    )
    cli.main()
    assert capsys.readouterr().out.splitlines() == [
        "baselines=5",
        "perturbed=15",
        "scores=15",
        f"report={report.resolve()}",
    ]


def test_cli_run_suite_live_selects_openai_backend_with_mocked_backend_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """API: live mode only selects the existing route under a fully mocked call."""
    received: dict[str, object] = {}
    selected: list[str] = []

    def fake_run_suite(*args: object, **kwargs: object) -> SuiteResult:
        del args
        received.update(kwargs)
        suite._backend_for(
            ROOT / "tasks" / "SIEVE-T1",
            "baseline",
            live=bool(kwargs["live"]),
            model=str(kwargs["model"]),
        )
        return SuiteResult((), (), (), tmp_path.joinpath("report.html").resolve())

    def backend(model: str) -> object:
        selected.append(model)
        return object()

    monkeypatch.setattr("sieve.suite.OpenAIResponsesBackend", backend)
    monkeypatch.setattr("sieve.cli.run_suite", fake_run_suite)
    monkeypatch.setattr(
        "sys.argv", ["sieve", "run-suite", "--live", "--model", "test-model", "--short"]
    )
    cli.main()
    assert received == {"live": True, "model": "test-model", "short": True}
    assert selected == ["test-model"]
    assert "report=" in capsys.readouterr().out


def test_full_run_suite_report_has_visible_two_by_two_grid_fifteen_table_rows_and_honest_limitations_section(  # noqa: E501
    full_recorded_suite: SuiteResult,
) -> None:
    """UI: the static report exposes every Phase 4 visual element in its DOM."""
    report = full_recorded_suite.report_path.read_text(encoding="utf-8")
    assert report.count('<div class="two-by-two-cells">') == 1
    assert report.count("<article id=") == 4
    assert report.count("<tr>") == 16
    assert '<section id="honest-limitations"' in report
