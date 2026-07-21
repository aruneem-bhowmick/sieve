"""Browser-safe deterministic projection of recorded Sieve evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sieve.reporting import load_report_data, summarize_two_by_two

BUNDLE_VERSION = 1
SOURCE_FILENAMES = {
    "task.md",
    "package.json",
    "intervention_constraints.json",
    "intervention_hypotheses.json",
}


def build_replay_bundle(runs_dir: Path, tasks_dir: Path) -> dict[str, Any]:
    """Project persisted recorded evidence into a stable browser-only document."""
    data = load_report_data(runs_dir)
    entries = []
    for entry in data.entries:
        score = entry.score
        entries.append(
            {
                "task_id": score.task_id,
                "intervention_type": score.intervention_type,
                "patch_divergence": score.patch_divergence,
                "outcome_stability": score.outcome_stability,
                "faithfulness_score": score.faithfulness_score,
                "test_result": entry.perturbed_test_result.model_dump(mode="json"),
                "intervention": entry.intervention.model_dump(mode="json"),
                "final_diff": entry.final_diff,
            }
        )
    return {
        "version": BUNDLE_VERSION,
        "tasks": _task_sources(tasks_dir),
        "entries": entries,
        "counts": asdict(summarize_two_by_two(data.entries)),
    }


def write_replay_bundle(runs_dir: Path, tasks_dir: Path, output_path: Path) -> Path:
    """Write a deterministic replay bundle without retaining run IDs or timestamps."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_replay_bundle(runs_dir, tasks_dir), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return output_path


def _task_sources(tasks_dir: Path) -> list[dict[str, object]]:
    """Read only browser-editable files, never dependencies or binaries."""
    tasks: list[dict[str, object]] = []
    for task_dir in sorted(path for path in tasks_dir.iterdir() if path.is_dir()):
        files: dict[str, str] = {}
        for path in sorted(task_dir.rglob("*")):
            if not path.is_file() or "node_modules" in path.parts:
                continue
            relative = path.relative_to(task_dir).as_posix()
            if relative in SOURCE_FILENAMES or (
                relative.startswith(("src/", "tests/"))
                and path.suffix in {".ts", ".tsx"}
            ):
                files[relative] = path.read_text(encoding="utf-8")
        if "task.md" not in files:
            raise ValueError(f"task fixture has no task.md: {task_dir.name}")
        tasks.append({"task_id": task_dir.name, "files": files})
    return tasks
