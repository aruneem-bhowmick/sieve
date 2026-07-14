"""CI-gated golden score regression coverage for SIV-OPS-002."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from sieve.schemas import ScoreRecord, TraceRecord
from sieve.scoring import ScoreRunner, assert_nondegenerate

FIXTURES = Path(__file__).parent / "fixtures" / "phase3"


@dataclass(frozen=True)
class GoldenPair:
    """One frozen baseline/perturbed artifact pair and expected score."""

    name: str
    directory: Path


PAIRS = (
    GoldenPair("t1-int01", FIXTURES / "t1-int01"),
    GoldenPair("t3-int02", FIXTURES / "t3-int02"),
)


def _read_trace(path: Path) -> TraceRecord:
    return TraceRecord.model_validate_json(path.read_text(encoding="utf-8"))


def _read_expected(pair: GoldenPair) -> ScoreRecord:
    return ScoreRecord.model_validate_json(
        (pair.directory / "expected-score.json").read_text(encoding="utf-8")
    )


def _promote_pair(pair: GoldenPair, runs_dir: Path) -> tuple[TraceRecord, TraceRecord]:
    baseline = _read_trace(pair.directory / "baseline-trace.json")
    perturbed = _read_trace(pair.directory / "perturbed-trace.json")
    for label, trace in (("baseline", baseline), ("perturbed", perturbed)):
        run_dir = runs_dir / str(trace.run_id)
        run_dir.mkdir(parents=True)
        shutil.copy2(pair.directory / f"{label}-trace.json", run_dir / "trace.json")
        shutil.copytree(pair.directory / f"{label}-workspace", run_dir / "workspace")
    return baseline, perturbed


def _score_pair(pair: GoldenPair, runs_dir: Path) -> ScoreRecord:
    baseline, perturbed = _promote_pair(pair, runs_dir)
    written, score = ScoreRunner(runs_dir).score(baseline.run_id, perturbed.run_id)
    assert ScoreRecord.model_validate_json(written.read_text(encoding="utf-8")) == score
    return score


def test_phase3_expected_score_fixtures_validate_as_score_records() -> None:
    for pair in PAIRS:
        score = _read_expected(pair)
        assert score.task_id in {"SIEVE-T1", "SIEVE-T3"}


def test_phase3_golden_trace_fixtures_validate_as_trace_records() -> None:
    for pair in PAIRS:
        baseline = _read_trace(pair.directory / "baseline-trace.json")
        perturbed = _read_trace(pair.directory / "perturbed-trace.json")
        assert baseline.run_type == "baseline"
        assert perturbed.run_type == "perturbed"


def test_score_runner_consumes_each_promoted_trace_pair_and_workspace_snapshot_and_persists_the_matching_expected_score(  # noqa: E501
    tmp_path: Path,
) -> None:
    runs_dir = tmp_path / "runs"
    for pair in PAIRS:
        assert _score_pair(pair, runs_dir) == _read_expected(pair)


def test_golden_score_regression_smoke_t1_int01(tmp_path: Path) -> None:
    assert _score_pair(PAIRS[0], tmp_path / "runs") == _read_expected(PAIRS[0])


def test_two_golden_scores_are_in_range_and_nondegenerate(tmp_path: Path) -> None:
    scores = [_score_pair(pair, tmp_path / "runs") for pair in PAIRS]
    first, second = scores
    assert all(0.0 <= score.patch_divergence <= 1.0 for score in scores)
    assert all(0.0 <= score.faithfulness_score <= 1.0 for score in scores)
    assert first.patch_divergence == first.faithfulness_score == 0.0
    assert first.outcome_stability is True
    assert second.patch_divergence > 0.0
    assert second.faithfulness_score == second.patch_divergence
    assert second.outcome_stability is False
    assert_nondegenerate(scores)


def test_phase3_golden_scores_remain_stable(tmp_path: Path) -> None:
    results = [_score_pair(pair, tmp_path / "runs") for pair in PAIRS]
    assert results == [_read_expected(pair) for pair in PAIRS]
    assert_nondegenerate(results)
