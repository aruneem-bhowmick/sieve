"""Run-artifact storage under the fixed ``runs/<run_id>/`` layout."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sieve.schemas import ScoreRecord, TraceRecord


def create_run_directory(runs_dir: Path, run_id: UUID) -> Path:
    """Create the immutable artifact directory for one run."""
    run_dir = runs_dir / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_trace(run_dir: Path, trace: TraceRecord) -> Path:
    """Serialize a validated trace record to its canonical JSON path."""
    path = run_dir / "trace.json"
    path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")
    return path


def write_score(run_dir: Path, score: ScoreRecord) -> Path:
    """Serialize a validated §5.3 score beside its perturbed trace."""
    path = run_dir / "score.json"
    path.write_text(score.model_dump_json(indent=2), encoding="utf-8")
    return path
