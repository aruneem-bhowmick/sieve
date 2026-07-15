"""Phase 4 recorded full-suite orchestration."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sieve.agent import (
    InterventionCodingAgentBackend,
    OpenAIResponsesBackend,
    RecordedBackend,
)
from sieve.interventions import (
    ClaimDeletion,
    ConstraintSwap,
    HypothesisFlip,
    InterventionRunner,
)
from sieve.reporting import write_report
from sieve.runner import TaskRunner
from sieve.schemas import ScoreRecord, StructuredReasoningStep, TraceRecord
from sieve.scoring import ScoreRunner, assert_nondegenerate

TASK_IDS: tuple[str, str, str, str, str] = (
    "SIEVE-T1",
    "SIEVE-T2",
    "SIEVE-T3",
    "SIEVE-T4",
    "SIEVE-T5",
)
INTERVENTION_TYPES: tuple[str, str, str] = ("INT-01", "INT-02", "INT-03")


@dataclass(frozen=True)
class SuiteResult:
    """Immutable paths and IDs written by one completed suite invocation."""

    baseline_run_ids: Sequence[UUID]
    perturbed_run_ids: Sequence[UUID]
    score_paths: Sequence[Path]
    report_path: Path


def target_step_id_for(baseline: TraceRecord) -> str:
    """Return the one deterministic Phase 4 target for a baseline trace."""
    if not baseline.steps:
        raise ValueError(f"baseline for {baseline.task_id} has no targetable steps")
    target = baseline.steps[0].step_id
    if not target.endswith("-S001"):
        raise ValueError(
            f"baseline for {baseline.task_id} must begin at an S001 step, got {target}"
        )
    return target


def matrix_keys(short: bool = False) -> tuple[tuple[str, str], ...]:
    """Return the fixed full matrix or the single fast offline smoke pair."""
    if short:
        return (("SIEVE-T1", "INT-01"),)
    return tuple(
        (task_id, intervention_type)
        for task_id in TASK_IDS
        for intervention_type in INTERVENTION_TYPES
    )


def run_suite(
    repo_root: Path,
    runs_dir: Path,
    report_path: Path,
    live: bool = False,
    model: str = "gpt-5.6",
    short: bool = False,
) -> SuiteResult:
    """Run the deterministic recorded Phase 4 matrix and render its report."""
    root = repo_root.resolve()
    output_runs = runs_dir.resolve()
    output_report = report_path.resolve()
    _validate_output_paths(output_runs, output_report)
    pairs = matrix_keys(short)
    _validate_matrix(pairs, short=short)

    baseline_run_ids: list[UUID] = []
    perturbed_run_ids: list[UUID] = []
    score_paths: list[Path] = []
    scores: list[ScoreRecord] = []
    runner = TaskRunner(root, output_runs)
    intervention_runner = InterventionRunner(root, output_runs)
    scorer = ScoreRunner(output_runs)

    with _copied_workspace_vitest_available(root):
        for task_id in dict.fromkeys(task for task, _ in pairs):
            task_dir = root / "tasks" / task_id
            baseline_backend = _backend_for(
                task_dir, "baseline", live=live, model=model
            )
            baseline_dir, baseline = runner.run(task_id, baseline_backend)
            baseline_run_ids.append(baseline.run_id)
            target = target_step_id_for(baseline)
            baseline_step = baseline.steps[0]

            for pair_task, intervention_type in (
                pair for pair in pairs if pair[0] == task_id
            ):
                if pair_task != task_id:
                    raise AssertionError(
                        "suite matrix task grouping changed unexpectedly"
                    )
                intervention = _intervention_for(task_dir, intervention_type, target)
                _validate_target_alternative(
                    task_id, intervention_type, intervention, baseline_step
                )
                perturbed_backend = _backend_for(
                    task_dir, intervention_type, live=live, model=model
                )
                perturbed_dir, perturbed = intervention_runner.run(
                    baseline,
                    baseline_dir,
                    target,
                    intervention,
                    perturbed_backend,
                )
                score_path, score = scorer.score(baseline.run_id, perturbed.run_id)
                perturbed_run_ids.append(perturbed.run_id)
                score_paths.append(score_path)
                scores.append(score)

    if not short:
        _validate_completed_scores(scores, pairs)
    written_report = write_report(output_runs, output_report)
    return SuiteResult(
        baseline_run_ids=tuple(baseline_run_ids),
        perturbed_run_ids=tuple(perturbed_run_ids),
        score_paths=tuple(score_paths),
        report_path=written_report.resolve(),
    )


def _validate_output_paths(runs_dir: Path, report_path: Path) -> None:
    if runs_dir.exists():
        raise FileExistsError(
            f"refusing to overwrite existing runs directory: {runs_dir}"
        )
    if report_path.exists():
        raise FileExistsError(f"refusing to overwrite existing report: {report_path}")


def _validate_matrix(pairs: Sequence[tuple[str, str]], short: bool) -> None:
    expected = (
        (("SIEVE-T1", "INT-01"),)
        if short
        else tuple(
            (task_id, intervention_type)
            for task_id in TASK_IDS
            for intervention_type in INTERVENTION_TYPES
        )
    )
    if len(pairs) != len(set(pairs)):
        raise ValueError("suite matrix contains duplicate task/intervention keys")
    if tuple(pairs) != expected:
        raise ValueError(
            "suite matrix is incomplete or differs from the required matrix"
        )


def _backend_for(
    task_dir: Path, kind: str, *, live: bool, model: str
) -> InterventionCodingAgentBackend:
    if live:
        return OpenAIResponsesBackend(model)
    filenames = {
        "baseline": "recorded_run.json",
        "INT-01": "recorded_int01_run.json",
        "INT-02": "recorded_int02_run.json",
        "INT-03": "recorded_int03_run.json",
    }
    recording = task_dir / filenames[kind]
    if not recording.is_file():
        raise FileNotFoundError(
            f"missing required {kind} recording for {task_dir.name}: {recording}"
        )
    return RecordedBackend.from_file(recording)


def _intervention_for(
    task_dir: Path, intervention_type: str, target: str
) -> ClaimDeletion | ConstraintSwap | HypothesisFlip:
    if intervention_type == "INT-01":
        return ClaimDeletion()
    try:
        if intervention_type == "INT-02":
            return ConstraintSwap.from_task_fixture(task_dir)
        if intervention_type == "INT-03":
            return HypothesisFlip.from_task_fixture(task_dir)
    except (FileNotFoundError, ValueError) as error:
        raise ValueError(
            f"{task_dir.name} {intervention_type} target {target}: {error}"
        ) from error
    raise ValueError(f"unsupported suite intervention: {intervention_type}")


def _validate_target_alternative(
    task_id: str,
    intervention_type: str,
    intervention: ClaimDeletion | ConstraintSwap | HypothesisFlip,
    baseline_step: StructuredReasoningStep,
) -> None:
    if intervention_type == "INT-01":
        return
    try:
        intervention.edit(baseline_step)
    except ValueError as error:
        raise ValueError(
            f"{task_id} {intervention_type} has no valid alternative for "
            f"{baseline_step.step_id}: {error}"
        ) from error


def _validate_completed_scores(
    scores: Sequence[ScoreRecord], pairs: Sequence[tuple[str, str]]
) -> None:
    score_keys = tuple((score.task_id, score.intervention_type) for score in scores)
    if len(scores) != 15 or set(score_keys) != set(pairs) or len(set(score_keys)) != 15:
        raise ValueError(
            "completed full suite has an incomplete or duplicate score matrix"
        )
    has_faithful = any(
        score.patch_divergence > 0.0 and not score.outcome_stability for score in scores
    )
    has_unfaithful = any(
        score.patch_divergence == 0.0 and score.outcome_stability for score in scores
    )
    if not has_faithful:
        raise ValueError("completed full suite lacks a faithful demo category")
    if not has_unfaithful:
        raise ValueError("completed full suite lacks an unfaithful demo category")
    assert_nondegenerate(scores)


@contextmanager
def _copied_workspace_vitest_available(repo_root: Path) -> Iterator[None]:
    """Expose the repository-pinned Vitest executable to copied task workspaces."""
    bin_dir = repo_root / "node_modules" / ".bin"
    if not bin_dir.is_dir():
        raise FileNotFoundError(f"missing pinned Vitest binary directory: {bin_dir}")
    previous = os.environ.get("Path")
    os.environ["Path"] = f"{bin_dir}{os.pathsep}{previous or ''}"
    try:
        yield
    finally:
        if previous is None:
            del os.environ["Path"]
        else:
            os.environ["Path"] = previous
