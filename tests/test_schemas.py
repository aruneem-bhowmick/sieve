from uuid import uuid4

import pytest
from pydantic import ValidationError

from sieve.schemas import (
    InterventionMetadata,
    PlannedAction,
    StructuredReasoningStep,
    TestResult,
    TraceRecord,
)


def step(number: int = 1) -> StructuredReasoningStep:
    return StructuredReasoningStep(
        step_id=f"TSIEVE-T1-S{number:03d}",
        claim="claim",
        constraint="constraint",
        hypothesis="hypothesis",
        planned_action=PlannedAction.READ_FILE,
        action_target="src/file.ts",
        success_criterion="criterion",
    )


def test_structured_step_round_trip() -> None:
    assert (
        StructuredReasoningStep.model_validate_json(step().model_dump_json()) == step()
    )


def test_structured_step_rejects_unknown_actions() -> None:
    with pytest.raises(ValidationError):
        StructuredReasoningStep.model_validate(
            {**step().model_dump(), "planned_action": "delete"}
        )


def test_trace_rejects_non_monotonic_step_ids() -> None:
    with pytest.raises(ValidationError, match="monotonically"):
        TraceRecord(
            task_id="SIEVE-T1",
            run_id=uuid4(),
            run_type="baseline",
            intervention=InterventionMetadata(),
            steps=[step(2), step(1)],
            final_diff="",
            test_result=TestResult(passed=[], failed=[]),
        )


def test_test_result_rejects_overlapping_outcomes() -> None:
    with pytest.raises(ValidationError, match="both pass and fail"):
        TestResult(passed=["case-1"], failed=["case-1"])
