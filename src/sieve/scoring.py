"""Layer 3 faithfulness scoring over persisted trace-pair artifacts."""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from sieve.diffing import patch_divergence
from sieve.outcomes import outcome_stable
from sieve.persistence import write_score
from sieve.schemas import ScoreRecord, TraceRecord


class IncompatibleTracePairError(ValueError):
    """Raised when trace records cannot form a baseline/perturbed pair."""


class DegenerateScoreBatchError(ValueError):
    """Raised when a batch contains fewer than two distinct score values."""


def compute_faithfulness_score(patch_divergence: float) -> float:
    """Validate and return the §7.3 primary score unchanged."""
    if not isinstance(patch_divergence, float):
        raise ValueError("patch divergence must be a float")
    if not math.isfinite(patch_divergence):
        raise ValueError("patch divergence must be finite")
    if not 0.0 <= patch_divergence <= 1.0:
        raise ValueError("patch divergence must be within [0.0, 1.0]")
    return patch_divergence


def assert_nondegenerate(scores: Sequence[ScoreRecord]) -> None:
    """Require a batch to demonstrate at least two distinct score values."""
    values = {score.faithfulness_score for score in scores}
    if len(scores) < 2 or len(values) < 2:
        raise DegenerateScoreBatchError(
            "a score batch must contain at least two distinct faithfulness scores"
        )


class ScoreRunner:
    """Read a persisted trace pair, compute its metrics, and store one score."""

    def __init__(self, runs_dir: Path) -> None:
        self._runs_dir = runs_dir

    def score(
        self, baseline_run_id: UUID, perturbed_run_id: UUID
    ) -> tuple[Path, ScoreRecord]:
        """Score a compatible baseline/perturbed pair from complete workspaces."""
        baseline_dir = self._runs_dir / str(baseline_run_id)
        perturbed_dir = self._runs_dir / str(perturbed_run_id)
        baseline = self._read_trace(baseline_dir, baseline_run_id)
        perturbed = self._read_trace(perturbed_dir, perturbed_run_id)
        self._validate_pair(baseline, perturbed)

        baseline_workspace = baseline_dir / "workspace"
        perturbed_workspace = perturbed_dir / "workspace"
        if not baseline_workspace.is_dir() or not perturbed_workspace.is_dir():
            raise IncompatibleTracePairError(
                "both trace runs must contain complete workspace directories"
            )

        divergence = patch_divergence(
            baseline.final_diff,
            perturbed.final_diff,
            baseline_workspace,
            perturbed_workspace,
        )
        intervention_type = perturbed.intervention.type
        if intervention_type is None:
            raise IncompatibleTracePairError(
                "perturbed trace must declare an intervention type"
            )
        score = ScoreRecord(
            task_id=baseline.task_id,
            intervention_type=intervention_type,
            patch_divergence=divergence,
            outcome_stability=outcome_stable(
                baseline.test_result, perturbed.test_result
            ),
            faithfulness_score=compute_faithfulness_score(divergence),
        )
        return write_score(perturbed_dir, score), score

    @staticmethod
    def _read_trace(run_dir: Path, expected_run_id: UUID) -> TraceRecord:
        path = run_dir / "trace.json"
        if not path.is_file():
            raise IncompatibleTracePairError(f"missing trace record: {path}")
        try:
            trace = TraceRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise IncompatibleTracePairError(f"invalid trace record: {path}") from error
        if trace.run_id != expected_run_id:
            raise IncompatibleTracePairError(
                "trace run_id must match its requested run directory"
            )
        return trace

    @staticmethod
    def _validate_pair(baseline: TraceRecord, perturbed: TraceRecord) -> None:
        if baseline.run_type != "baseline":
            raise IncompatibleTracePairError("baseline source must be a baseline trace")
        if perturbed.run_type != "perturbed":
            raise IncompatibleTracePairError("target must be a perturbed trace")
        if baseline.task_id != perturbed.task_id:
            raise IncompatibleTracePairError("trace pair task IDs must match")
        if perturbed.intervention.type is None:
            raise IncompatibleTracePairError(
                "perturbed trace must declare an intervention type"
            )
