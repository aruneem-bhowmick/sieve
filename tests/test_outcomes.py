"""Tests for the §7.2 test-outcome stability comparison."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from sieve.agent import RecordedBackend
from sieve.outcomes import outcome_stable
from sieve.runner import TaskRunner
from sieve.schemas import TestResult, TraceRecord

ROOT = Path(__file__).resolve().parents[1]


def test_same_pass_fail_sets_are_stable() -> None:
    baseline = TestResult(passed=["alpha"], failed=["beta"])
    perturbed = TestResult(passed=["alpha"], failed=["beta"])

    assert outcome_stable(baseline, perturbed) is True


def test_reordered_test_ids_are_stable() -> None:
    baseline = TestResult(passed=["alpha", "beta"], failed=["gamma", "delta"])
    perturbed = TestResult(passed=["beta", "alpha"], failed=["delta", "gamma"])

    assert outcome_stable(baseline, perturbed) is True


def test_moved_test_id_from_passed_to_failed_is_unstable() -> None:
    baseline = TestResult(passed=["alpha", "beta"], failed=[])
    perturbed = TestResult(passed=["alpha"], failed=["beta"])

    assert outcome_stable(baseline, perturbed) is False


def test_added_or_removed_test_id_is_unstable() -> None:
    baseline = TestResult(passed=["alpha"], failed=[])
    perturbed = TestResult(passed=["alpha", "beta"], failed=[])

    assert outcome_stable(baseline, perturbed) is False


def test_phase2_trace_records_feed_outcome_stability_without_raw_output_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    t1_baseline = TraceRecord.model_validate_json(
        (ROOT / "tests/fixtures/phase1/SIEVE-T1-baseline-trace.json").read_text(
            encoding="utf-8"
        )
    )
    t1_perturbed = TraceRecord.model_validate_json(
        (ROOT / "tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json").read_text(
            encoding="utf-8"
        )
    )
    _, t3_baseline = TaskRunner(ROOT, tmp_path / "runs").run(
        "SIEVE-T3",
        RecordedBackend.from_file(ROOT / "tasks/SIEVE-T3/recorded_run.json"),
    )
    t3_perturbed = TraceRecord.model_validate_json(
        (ROOT / "tests/fixtures/phase2/SIEVE-T3-int02-perturbed-trace.json").read_text(
            encoding="utf-8"
        )
    )

    assert outcome_stable(t1_baseline.test_result, t1_perturbed.test_result) is True
    assert outcome_stable(t3_baseline.test_result, t3_perturbed.test_result) is False


def test_outcome_stability_smoke_one_passing_id() -> None:
    outcome = TestResult(passed=["vitest"], failed=[])

    assert outcome_stable(outcome, outcome) is True


def test_outcome_stability_is_boolean_for_empty_equal_and_different_sets() -> None:
    empty = TestResult(passed=[], failed=[])
    equal = TestResult(passed=["alpha"], failed=["beta"])
    different = TestResult(passed=["alpha"], failed=[])

    assert isinstance(outcome_stable(empty, empty), bool)
    assert isinstance(
        outcome_stable(equal, TestResult(passed=["alpha"], failed=["beta"])), bool
    )
    assert isinstance(outcome_stable(equal, different), bool)
