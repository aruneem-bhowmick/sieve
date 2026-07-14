"""Layer 2 implementations of causal trace interventions."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from uuid import uuid4

from sieve.agent import AgentTurn, InterventionCodingAgentBackend
from sieve.budget import StepBudget
from sieve.persistence import create_run_directory, write_trace
from sieve.replay import ReplayContextItem, build_replay_context
from sieve.runner import TaskRunner, unified_directory_diff
from sieve.schemas import (
    InterventionMetadata,
    StructuredReasoningStep,
    TestResult,
    ToolResultRecord,
    TraceRecord,
)


class ClaimDeletion:
    """INT-01: blank a target step's factual claim and resume."""

    type: Literal["INT-01"] = "INT-01"
    target_field: Literal["claim"] = "claim"

    def edit(self, baseline_step: StructuredReasoningStep) -> StructuredReasoningStep:
        """Return the source step with exactly its claim replaced by ``""``."""
        return baseline_step.model_copy(update={"claim": ""})

    def metadata(self, baseline_step: StructuredReasoningStep) -> InterventionMetadata:
        """Return complete §5.2 metadata for the deleted claim."""
        return InterventionMetadata(
            type=self.type,
            target_step_id=baseline_step.step_id,
            target_field=self.target_field,
            original_value=baseline_step.claim,
            replacement_value="",
        )


class ConstraintSwap:
    """INT-02: replace a step constraint with a reviewed task-local alternative."""

    type: Literal["INT-02"] = "INT-02"
    target_field: Literal["constraint"] = "constraint"

    def __init__(self, alternative_constraints: Mapping[str, str]) -> None:
        """Store non-empty, task-authored alternatives by exact step identifier."""
        if not alternative_constraints:
            raise ValueError("constraint swaps must not be empty")
        validated: dict[str, str] = {}
        for step_id, alternative in alternative_constraints.items():
            if not isinstance(step_id, str) or not isinstance(alternative, str):
                raise ValueError("constraint swap mappings must contain strings")
            if not alternative.strip():
                raise ValueError("constraint alternatives must be non-empty")
            validated[step_id] = alternative
        self._alternative_constraints = validated

    @classmethod
    def from_task_fixture(cls, task_dir: Path) -> ConstraintSwap:
        """Load and validate the reviewed alternatives stored beside a task fixture."""
        path = task_dir / "intervention_constraints.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing intervention constraint fixture: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("invalid intervention constraint JSON") from error
        if not isinstance(raw, dict):
            raise ValueError("constraint fixture must be an object")
        alternatives = raw.get("constraint_swaps")
        reviews = raw.get("manual_reviews")
        if not isinstance(alternatives, dict) or not isinstance(reviews, dict):
            raise ValueError(
                "constraint fixture requires constraint_swaps and manual_reviews"
            )
        if set(alternatives) != set(reviews) or not alternatives:
            raise ValueError("every constraint swap requires an alternative and review")
        for step_id, review in reviews.items():
            if not isinstance(step_id, str) or not isinstance(review, str):
                raise ValueError("constraint reviews must contain strings")
            if not review.strip():
                raise ValueError("constraint reviews must be non-empty")
        return cls(alternatives)

    def edit(self, baseline_step: StructuredReasoningStep) -> StructuredReasoningStep:
        """Replace only the exact target constraint with its reviewed alternative."""
        alternative = self._alternative_constraints.get(baseline_step.step_id)
        if alternative is None:
            raise ValueError(
                f"no constraint swap alternative for step: {baseline_step.step_id}"
            )
        if alternative == baseline_step.constraint:
            raise ValueError("constraint replacement must differ from the baseline")
        return baseline_step.model_copy(update={"constraint": alternative})

    def metadata(self, baseline_step: StructuredReasoningStep) -> InterventionMetadata:
        """Return complete §5.2 metadata for the selected constraint replacement."""
        edited = self.edit(baseline_step)
        return InterventionMetadata(
            type=self.type,
            target_step_id=baseline_step.step_id,
            target_field=self.target_field,
            original_value=baseline_step.constraint,
            replacement_value=edited.constraint,
        )


class InterventionRunner:
    """Persist a perturbed trace regenerated from one edited target step."""

    def __init__(
        self, repo_root: Path, runs_dir: Path, max_resumed_steps: int = 20
    ) -> None:
        """Configure artifact storage and the bounded regenerated suffix."""
        self._repo_root = repo_root
        self._runs_dir = runs_dir
        self._max_resumed_steps = max_resumed_steps

    def run(
        self,
        baseline: TraceRecord,
        baseline_run_dir: Path,
        target_step_id: str,
        intervention: ClaimDeletion | ConstraintSwap,
        backend: InterventionCodingAgentBackend,
    ) -> tuple[Path, TraceRecord]:
        """Execute an edited target and persist a distinct perturbed trace."""
        if baseline.run_type != "baseline":
            raise ValueError("interventions require a baseline source trace")
        if intervention.type not in {"INT-01", "INT-02"}:
            raise ValueError("unsupported intervention type")
        if intervention.type == "INT-01" and intervention.target_field != "claim":
            raise ValueError("ClaimDeletion must target the claim field")
        if intervention.type == "INT-02" and intervention.target_field != "constraint":
            raise ValueError("ConstraintSwap must target the constraint field")
        if not hasattr(backend, "intervention_turn") or not hasattr(
            backend, "resume_turn"
        ):
            raise TypeError("backend must implement intervention_turn and resume_turn")

        replay_context = build_replay_context(baseline, target_step_id)
        prefix_length = len(replay_context)
        if prefix_length and len(baseline.tool_results) != len(baseline.steps):
            raise ValueError("baseline fixed prefix requires paired tool_results")
        baseline_step = baseline.steps[prefix_length]
        edited_step = intervention.edit(baseline_step)
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
        steps = list(baseline.steps[:prefix_length])
        tool_results = list(baseline.tool_results[:prefix_length])
        test_result = TestResult(passed=[], failed=[])
        executor = TaskRunner(self._repo_root, self._runs_dir)
        budget = StepBudget(self._max_resumed_steps)

        turn = backend.intervention_turn(
            prompt, replay_context, edited_step, tool_results
        )
        if turn is None:
            raise ValueError(
                "intervention backend did not return an edited target turn"
            )
        self._validate_first_turn(turn, edited_step)
        _, latest_tests = self._execute_turn(
            executor, workspace, turn, steps, tool_results, budget, test_result
        )
        if latest_tests is not None:
            test_result = latest_tests

        continuation = [
            *replay_context,
            ReplayContextItem(
                step_id=edited_step.step_id, content=edited_step.model_dump_json()
            ),
        ]
        while True:
            turn = backend.resume_turn(prompt, continuation, tool_results)
            if turn is None:
                break
            self._validate_continuation(baseline.task_id, steps, turn)
            result, latest_tests = self._execute_turn(
                executor, workspace, turn, steps, tool_results, budget, test_result
            )
            if latest_tests is not None:
                test_result = latest_tests
            del result

        final_diff = unified_directory_diff(fixture, workspace)
        trace = TraceRecord(
            task_id=baseline.task_id,
            run_id=run_id,
            run_type="perturbed",
            intervention=intervention.metadata(baseline_step),
            steps=steps,
            tool_results=tool_results,
            final_diff=final_diff,
            test_result=test_result,
        )
        (run_dir / "final.diff").write_text(final_diff, encoding="utf-8")
        write_trace(run_dir, trace)
        return run_dir, trace

    @staticmethod
    def _validate_first_turn(
        turn: AgentTurn, edited_step: StructuredReasoningStep
    ) -> None:
        """Reject a backend that attempts to restore the unedited target."""
        if turn.step != edited_step:
            raise ValueError("first generated step must equal the edited target")

    @staticmethod
    def _validate_continuation(
        task_id: str, steps: list[StructuredReasoningStep], turn: AgentTurn
    ) -> None:
        """Require task-local, strictly increasing generated continuation IDs."""
        prefix = f"T{task_id}-S"
        if not turn.step.step_id.startswith(prefix):
            raise ValueError("generated step ID must belong to the baseline task")
        previous = steps[-1].step_id.removeprefix(prefix)
        current = turn.step.step_id.removeprefix(prefix)
        if int(current) <= int(previous):
            raise ValueError("generated step ID must follow the edited target")

    @staticmethod
    def _execute_turn(
        executor: TaskRunner,
        workspace: Path,
        turn: AgentTurn,
        steps: list[StructuredReasoningStep],
        tool_results: list[ToolResultRecord],
        budget: StepBudget,
        test_result: TestResult,
    ) -> tuple[ToolResultRecord, TestResult | None]:
        """Execute and append one inseparable structured-step/result pair."""
        del test_result
        budget.consume()
        result, latest_tests = executor._execute_turn(workspace, turn)
        steps.append(turn.step)
        tool_results.append(result)
        return result, latest_tests
