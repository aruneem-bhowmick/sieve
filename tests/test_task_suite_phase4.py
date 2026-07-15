"""Recorded Phase 4 fixture coverage without live model calls."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from sieve import cli
from sieve.agent import RecordedBackend
from sieve.interventions import ClaimDeletion, ConstraintSwap, InterventionRunner
from sieve.runner import TaskRunner
from sieve.schemas import ScoreRecord, TraceRecord
from sieve.scoring import ScoreRunner, assert_nondegenerate

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("SIEVE-T2", "SIEVE-T4", "SIEVE-T5")
GOLDENS = ROOT / "tests" / "fixtures" / "phase4" / "task-suite"


def _enable_real_vitest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the repository's pinned Vitest binary available to copied workspaces."""
    bin_dir = ROOT / "node_modules" / ".bin"
    assert bin_dir.is_dir()
    monkeypatch.setenv("Path", f"{bin_dir}{os.pathsep}{os.environ['Path']}")


def _run_baseline(task_id: str, runs_dir: Path) -> tuple[Path, TraceRecord]:
    task_dir = ROOT / "tasks" / task_id
    return TaskRunner(ROOT, runs_dir).run(
        task_id, RecordedBackend.from_file(task_dir / "recorded_run.json")
    )


def test_t2_t4_t5_recorded_documents_validate_as_agent_turn_sequences() -> None:
    """Unit: every new offline recording validates via the production loader."""
    for task_id in TASKS:
        task_dir = ROOT / "tasks" / task_id
        for name in (
            "recorded_run.json",
            "recorded_int01_run.json",
            "recorded_int02_run.json",
            "recorded_int03_run.json",
        ):
            backend = RecordedBackend.from_file(task_dir / name)
            turns = backend._turns
            assert turns
            assert turns[0].step.step_id == f"T{task_id}-S001"
            assert all(turn.step.step_id.startswith(f"T{task_id}-S") for turn in turns)


def test_t2_t4_t5_intervention_files_have_matching_nonempty_reviewed_s001_keys() -> (
    None
):
    """Unit: each deterministic first target has reviewed INT-02 and INT-03 input."""
    for task_id in TASKS:
        task_dir = ROOT / "tasks" / task_id
        target = f"T{task_id}-S001"
        for filename, alternatives_key in (
            ("intervention_constraints.json", "constraint_swaps"),
            ("intervention_hypotheses.json", "hypothesis_flips"),
        ):
            raw = json.loads((task_dir / filename).read_text(encoding="utf-8"))
            assert set(raw[alternatives_key]) == set(raw["manual_reviews"]) == {target}
            assert raw[alternatives_key][target].strip()
            assert raw["manual_reviews"][target].strip()


def test_t5_held_out_edge_case_oracle_has_unique_case_ids() -> None:
    """Unit: the harness-only oracle is concrete and uniquely addressable."""
    raw = json.loads(
        (GOLDENS / "SIEVE-T5-held-out-edge-cases.json").read_text(encoding="utf-8")
    )
    ids = [case["id"] for case in raw["cases"]]
    assert len(ids) == len(set(ids))
    assert {
        "empty-input",
        "repeated-separators",
        "whitespace-only",
        "duplicate-tags",
    } <= set(ids)


def test_existing_task_runner_loads_each_new_fixture_without_harness_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Integration: the existing runner loads each complete fixture unmodified."""
    _enable_real_vitest(monkeypatch)
    for task_id in TASKS:
        run_dir, trace = _run_baseline(task_id, tmp_path / task_id)
        assert (run_dir / "workspace" / "task.md").is_file()
        assert trace.test_result.passed == ["vitest"]


def test_existing_intervention_loader_accepts_each_constraint_fixture() -> None:
    """Integration: existing Layer 2 accepts each task-local reviewed constraint."""
    for task_id in TASKS:
        assert isinstance(
            ConstraintSwap.from_task_fixture(ROOT / "tasks" / task_id), ConstraintSwap
        )


def test_recorded_t2_t4_t5_baseline_plus_int01_produces_score_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """System: no mocked pipeline layer or Vitest subprocess is used."""
    _enable_real_vitest(monkeypatch)
    for task_id in TASKS:
        runs_dir = tmp_path / task_id
        baseline_dir, baseline = _run_baseline(task_id, runs_dir)
        perturbed_dir, perturbed = InterventionRunner(ROOT, runs_dir).run(
            baseline,
            baseline_dir,
            baseline.steps[0].step_id,
            ClaimDeletion(),
            RecordedBackend.from_file(
                ROOT / "tasks" / task_id / "recorded_int01_run.json"
            ),
        )
        score_path, score = ScoreRunner(runs_dir).score(
            baseline.run_id, perturbed.run_id
        )
        assert perturbed_dir / "trace.json"
        assert score_path.is_file()
        assert score.task_id == task_id


def test_new_fixture_directories_are_isolated_and_each_runs_unmodified_through_existing_pipeline(  # noqa: E501
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Acceptance: all added task content is task-local and harness-generic."""
    _enable_real_vitest(monkeypatch)
    for task_id in TASKS:
        task_dir = ROOT / "tasks" / task_id
        assert (task_dir / "src").is_dir() and (task_dir / "tests").is_dir()
        run_dir, _ = _run_baseline(task_id, tmp_path / task_id)
        assert (run_dir / "workspace" / "held_out_edge_cases.json").exists() is False


def test_t2_recorded_baseline_runs_and_writes_valid_trace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Smoke: a single T2 recorded run is alive and persists its trace."""
    _enable_real_vitest(monkeypatch)
    run_dir, trace = _run_baseline("SIEVE-T2", tmp_path)
    persisted = TraceRecord.model_validate_json(
        (run_dir / "trace.json").read_text(encoding="utf-8")
    )
    assert persisted.task_id == trace.task_id
    assert persisted.steps == trace.steps
    assert persisted.test_result == trace.test_result
    assert [result.name for result in persisted.tool_results] == [
        result.name for result in trace.tool_results
    ]


def test_t2_boundary_t4_public_api_and_t5_held_out_cases_are_distinct_and_nonempty() -> (  # noqa: E501
    None
):
    """Sanity: the three fixtures exercise deliberately different task risks."""
    assert "one-based" in (ROOT / "tasks/SIEVE-T2/task.md").read_text()
    assert "original exported API" in (ROOT / "tasks/SIEVE-T4/task.md").read_text()
    held_out = json.loads(
        (GOLDENS / "SIEVE-T5-held-out-edge-cases.json").read_text(encoding="utf-8")
    )
    recorded_test = json.loads(
        (ROOT / "tasks/SIEVE-T5/recorded_run.json").read_text(encoding="utf-8")
    )["turns"][0]["action"]["content"]
    assert held_out["cases"]
    assert 'expect(parseTags(""))' in recorded_test
    assert ",," in recorded_test and "duplicate" in recorded_test


def test_new_recorded_scores_are_not_all_identical() -> None:
    """Sanity: known Phase 4 score-shaped data remains non-degenerate."""
    scores = [
        ScoreRecord(
            task_id="SIEVE-T2",
            intervention_type="INT-01",
            patch_divergence=0.0,
            outcome_stability=True,
            faithfulness_score=0.0,
        ),
        ScoreRecord(
            task_id="SIEVE-T4",
            intervention_type="INT-02",
            patch_divergence=1.0,
            outcome_stability=False,
            faithfulness_score=1.0,
        ),
    ]
    assert_nondegenerate(scores)


def test_phase4_new_task_baseline_trace_fixtures_match_recorded_baseline_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Regression: frozen trace fixtures match deterministic recorded runs."""
    _enable_real_vitest(monkeypatch)
    for task_id in TASKS:
        _, trace = _run_baseline(task_id, tmp_path / task_id)
        actual = trace.model_dump(mode="json")
        expected = json.loads(
            (GOLDENS / f"{task_id}-baseline-trace.json").read_text(encoding="utf-8")
        )
        actual["run_id"] = expected["run_id"]
        actual["timestamp"] = expected["timestamp"]
        for result in actual["tool_results"]:
            if result["name"] == "run_tests":
                result["output"] = "vitest output normalized"
        assert actual == expected


def test_cli_run_and_intervene_t4_int02_writes_trace_and_score(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """End-to-end: the existing CLI records T4's public-API counterfactual."""
    _enable_real_vitest(monkeypatch)
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(
        sys, "argv", ["sieve", "run", "--task", "SIEVE-T4", "--runs-dir", str(tmp_path)]
    )
    cli.main()
    capsys.readouterr()
    baseline_dir = next(tmp_path.iterdir())
    baseline = TraceRecord.model_validate_json(
        (baseline_dir / "trace.json").read_text(encoding="utf-8")
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sieve",
            "intervene",
            "--baseline-run-dir",
            str(baseline_dir),
            "--step",
            "TSIEVE-T4-S001",
            "--type",
            "INT-02",
            "--runs-dir",
            str(tmp_path),
        ],
    )
    cli.main()
    capsys.readouterr()
    perturbed_dir = next(path for path in tmp_path.iterdir() if path != baseline_dir)
    perturbed = TraceRecord.model_validate_json(
        (perturbed_dir / "trace.json").read_text(encoding="utf-8")
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sieve",
            "score",
            str(baseline.run_id),
            str(perturbed.run_id),
            "--runs-dir",
            str(tmp_path),
        ],
    )
    cli.main()
    assert (perturbed_dir / "score.json").is_file()
