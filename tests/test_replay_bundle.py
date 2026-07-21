"""Recorded-evidence export coverage for the interactive browser demo."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from sieve.replay_bundle import BUNDLE_VERSION, build_replay_bundle, write_replay_bundle

ROOT = Path(__file__).resolve().parents[1]
REPORT_RUNS = ROOT / "tests" / "fixtures" / "phase4" / "reporting" / "two-score-runs"


def _tasks(destination: Path) -> Path:
    tasks = destination / "tasks"
    task = tasks / "SIEVE-T1"
    (task / "src").mkdir(parents=True)
    (task / "tests").mkdir()
    (task / "node_modules").mkdir()
    (task / "task.md").write_text("Fix it", encoding="utf-8")
    (task / "src" / "fix.ts").write_text("export {}", encoding="utf-8")
    (task / "tests" / "fix.test.ts").write_text("export {}", encoding="utf-8")
    (task / "node_modules" / "ignored.js").write_text("secret", encoding="utf-8")
    return tasks


def test_build_replay_bundle_projects_trace_metadata_without_run_identifiers(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    shutil.copytree(REPORT_RUNS, runs)

    bundle = build_replay_bundle(runs, _tasks(tmp_path))

    assert bundle["version"] == BUNDLE_VERSION
    assert [entry["task_id"] for entry in bundle["entries"]] == [
        "SIEVE-T1",
        "SIEVE-T3",
    ]
    entry = bundle["entries"][0]
    assert entry["intervention"]["original_value"]
    assert "run_id" not in entry
    assert "timestamp" not in entry
    assert bundle["tasks"] == [
        {
            "task_id": "SIEVE-T1",
            "files": {
                "src/fix.ts": "export {}",
                "task.md": "Fix it",
                "tests/fix.test.ts": "export {}",
            },
        }
    ]


def test_write_replay_bundle_is_deterministic_and_valid_json(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    shutil.copytree(REPORT_RUNS, runs)
    tasks = _tasks(tmp_path)
    first = write_replay_bundle(runs, tasks, tmp_path / "one.json")
    second = write_replay_bundle(runs, tasks, tmp_path / "two.json")

    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8"))["counts"] == {
        "changed_broke": 1,
        "changed_pass": 0,
        "unchanged_broke": 0,
        "unchanged_pass": 1,
    }
