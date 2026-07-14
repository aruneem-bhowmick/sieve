"""Layer 2 no-op trace resumption from a recorded baseline checkpoint."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from sieve.agent import (
    AgentTurn,
    ResumableCodingAgentBackend,
    ToolResult,
)
from sieve.budget import StepBudget
from sieve.persistence import create_run_directory, write_trace
from sieve.replay import ReplayContextItem, build_replay_context
from sieve.runner import TaskRunner, unified_directory_diff
from sieve.schemas import (
    InterventionMetadata,
    StructuredReasoningStep,
    TestResult,
    TraceRecord,
)


class ResumeRunner:
    """Regenerate a baseline suffix in a fresh workspace from fixed context."""

    def __init__(
        self, repo_root: Path, runs_dir: Path, max_resumed_steps: int = 20
    ) -> None:
        """Configure fixture discovery, artifact storage, and resume budget."""
        self._repo_root = repo_root
        self._runs_dir = runs_dir
        self._max_resumed_steps = max_resumed_steps

    def resume(
        self,
        baseline: TraceRecord,
        baseline_run_dir: Path,
        target_step_id: str,
        backend: ResumableCodingAgentBackend,
    ) -> tuple[Path, TraceRecord]:
        """Regenerate and persist an unmodified-field replay from one step."""
        if not hasattr(backend, "resume_turn"):
            raise TypeError("backend must implement resume_turn")
        replay_context = build_replay_context(baseline, target_step_id)
        checkpoint_name = replay_context[-1].step_id if replay_context else "initial"
        checkpoint = baseline_run_dir / "checkpoints" / checkpoint_name
        if not checkpoint.is_dir():
            raise FileNotFoundError(f"missing pre-target checkpoint: {checkpoint_name}")
        fixture = self._repo_root / "tasks" / baseline.task_id
        if not fixture.is_dir():
            raise FileNotFoundError(f"unknown task fixture: {baseline.task_id}")

        run_id = uuid4()
        run_dir = create_run_directory(self._runs_dir, run_id)
        workspace = run_dir / "workspace"
        shutil.copytree(checkpoint, workspace)
        prompt = (workspace / "task.md").read_text(encoding="utf-8")
        budget = StepBudget(self._max_resumed_steps)
        executor = TaskRunner(self._repo_root, self._runs_dir)
        history: list[ToolResult] = []
        steps = list(baseline.steps[: len(replay_context)])
        test_result = TestResult(passed=[], failed=[])

        while True:
            turn = backend.resume_turn(prompt, replay_context, history)
            if turn is None:
                break
            self._validate_generated_step(
                baseline, replay_context, steps, target_step_id, turn
            )
            budget.consume()
            result, latest_tests = executor._execute_turn(workspace, turn)
            history.append(result)
            steps.append(turn.step)
            if latest_tests is not None:
                test_result = latest_tests

        final_diff = unified_directory_diff(fixture, workspace)
        trace = TraceRecord(
            task_id=baseline.task_id,
            run_id=run_id,
            run_type="baseline",
            intervention=InterventionMetadata(),
            steps=steps,
            final_diff=final_diff,
            test_result=test_result,
        )
        (run_dir / "final.diff").write_text(final_diff, encoding="utf-8")
        write_trace(run_dir, trace)
        return run_dir, trace

    @staticmethod
    def _validate_generated_step(
        baseline: TraceRecord,
        replay_context: list[ReplayContextItem],
        steps: list[StructuredReasoningStep],
        target_step_id: str,
        turn: AgentTurn,
    ) -> None:
        """Reject generated steps that do not continue the fixed trace prefix."""
        prefix = f"T{baseline.task_id}-S"
        if not turn.step.step_id.startswith(prefix):
            raise ValueError("generated step ID must belong to the baseline task")
        generated_number = int(turn.step.step_id.removeprefix(prefix))
        if len(steps) == len(replay_context) and turn.step.step_id != target_step_id:
            raise ValueError("first generated step must equal the requested target")
        if replay_context:
            previous = steps[-1].step_id
            previous_number = int(previous.removeprefix(prefix))
            if generated_number <= previous_number:
                raise ValueError("generated step ID must follow fixed replay context")
