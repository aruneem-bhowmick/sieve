"""Layer 1 runner: execute an agent against an isolated task workspace."""

from __future__ import annotations

import difflib
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from sieve.agent import AgentTurn, CodingAgentBackend
from sieve.persistence import create_run_directory, write_trace
from sieve.schemas import (
    InterventionMetadata,
    PlannedAction,
    TestResult,
    ToolResultRecord,
    TraceRecord,
)


class TaskRunner:
    """Execute one task fixture against a backend in an isolated workspace."""

    def __init__(self, repo_root: Path, runs_dir: Path, max_steps: int = 20) -> None:
        """Configure fixture discovery, artifact storage, and a step limit."""
        self._repo_root = repo_root
        self._runs_dir = runs_dir
        self._max_steps = max_steps

    def run(
        self, task_id: str, backend: CodingAgentBackend
    ) -> tuple[Path, TraceRecord]:
        """Run a baseline task and persist its trace and final unified diff."""
        fixture = self._repo_root / "tasks" / task_id
        if not fixture.is_dir():
            raise FileNotFoundError(f"unknown task fixture: {task_id}")
        run_id = uuid4()
        run_dir = create_run_directory(self._runs_dir, run_id)
        workspace = run_dir / "workspace"
        shutil.copytree(fixture, workspace)
        checkpoints = run_dir / "checkpoints"
        checkpoints.mkdir()
        shutil.copytree(workspace, checkpoints / "initial")
        prompt = (workspace / "task.md").read_text(encoding="utf-8")
        tool_results: list[ToolResultRecord] = []
        steps = []
        test_result = TestResult(passed=[], failed=[])

        for _ in range(self._max_steps):
            turn = backend.next_turn(prompt, tool_results)
            if turn is None:
                break
            result, latest_tests = self._execute_turn(workspace, turn)
            tool_results.append(result)
            steps.append(turn.step)
            if result.succeeded:
                shutil.copytree(workspace, checkpoints / turn.step.step_id)
            if latest_tests is not None:
                test_result = latest_tests
        else:
            raise RuntimeError(
                f"agent exceeded Phase 0 step budget ({self._max_steps})"
            )

        final_diff = unified_directory_diff(fixture, workspace)
        trace = TraceRecord(
            task_id=task_id,
            run_id=run_id,
            run_type="baseline",
            intervention=InterventionMetadata(),
            steps=steps,
            tool_results=tool_results,
            final_diff=final_diff,
            test_result=test_result,
        )
        (run_dir / "final.diff").write_text(final_diff, encoding="utf-8")
        write_trace(run_dir, trace)
        return run_dir, trace

    def _execute_turn(
        self, workspace: Path, turn: AgentTurn
    ) -> tuple[ToolResultRecord, TestResult | None]:
        """Execute one validated local action and capture its observable result."""
        target = _workspace_path(workspace, turn.action.target)
        if turn.action.name == PlannedAction.READ_FILE:
            output = target.read_text(encoding="utf-8")
            result = ToolResultRecord(
                name=turn.action.name,
                target=turn.action.target,
                output=output,
                succeeded=True,
            )
            return result, None
        if turn.action.name == PlannedAction.EDIT_FILE:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(turn.action.content or "", encoding="utf-8")
            return (
                ToolResultRecord(
                    name=turn.action.name,
                    target=turn.action.target,
                    output="edited",
                    succeeded=True,
                ),
                None,
            )
        if turn.action.name == PlannedAction.SEARCH:
            matches = [
                str(path.relative_to(workspace))
                for path in workspace.rglob("*")
                if path.is_file() and _file_contains(path, turn.action.target)
            ]
            return (
                ToolResultRecord(
                    name=turn.action.name,
                    target=turn.action.target,
                    output="\n".join(matches),
                    succeeded=True,
                ),
                None,
            )
        if turn.action.name in {PlannedAction.RUN_TESTS, PlannedAction.RUN_COMMAND}:
            completed = subprocess.run(
                turn.action.target,
                cwd=workspace,
                shell=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            output = completed.stdout + completed.stderr
            result = ToolResultRecord(
                name=turn.action.name,
                target=turn.action.target,
                output=output,
                succeeded=completed.returncode == 0,
            )
            if turn.action.name == PlannedAction.RUN_TESTS:
                test_result = TestResult(
                    passed=["vitest"] if completed.returncode == 0 else [],
                    failed=[] if completed.returncode == 0 else ["vitest"],
                )
                return result, test_result
            return result, None
        raise ValueError(f"unsupported action: {turn.action.name}")


def _workspace_path(workspace: Path, target: str) -> Path:
    """Resolve a file tool target while preventing workspace escape."""
    candidate = (workspace / target).resolve()
    if not candidate.is_relative_to(workspace.resolve()):
        raise ValueError("tool target must remain inside the task workspace")
    return candidate


def _file_contains(path: Path, query: str) -> bool:
    """Return whether a UTF-8 fixture file contains the requested query."""
    return query in path.read_text(encoding="utf-8")


def unified_directory_diff(original: Path, changed: Path) -> str:
    """Return a stable unified diff over tracked fixture files only."""

    original_files = {
        path.relative_to(original)
        for path in original.rglob("*")
        if path.is_file() and "node_modules" not in path.parts
    }
    changed_files = {
        path.relative_to(changed)
        for path in changed.rglob("*")
        if path.is_file() and "node_modules" not in path.parts
    }
    lines: list[str] = []
    for relative in sorted(original_files | changed_files):
        before = (
            (original / relative).read_text(encoding="utf-8").splitlines(True)
            if relative in original_files
            else []
        )
        after = (
            (changed / relative).read_text(encoding="utf-8").splitlines(True)
            if relative in changed_files
            else []
        )
        lines.extend(
            difflib.unified_diff(
                before,
                after,
                fromfile=f"a/{relative.as_posix()}",
                tofile=f"b/{relative.as_posix()}",
            )
        )
    return "".join(lines)
