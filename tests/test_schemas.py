from uuid import uuid4

import pytest
from pydantic import ValidationError

from sieve.schemas import (
    InterventionMetadata,
    PlannedAction,
    StructuredReasoningStep,
    TestResult,
    ToolResultRecord,
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


def tool_result(number: int = 1) -> ToolResultRecord:
    return ToolResultRecord(
        name=PlannedAction.READ_FILE,
        target=f"src/file-{number}.ts",
        output=f"contents {number}",
        succeeded=True,
    )


def test_trace_accepts_ordered_tool_result_records() -> None:
    trace = TraceRecord(
        task_id="SIEVE-T1",
        run_id=uuid4(),
        run_type="baseline",
        intervention=InterventionMetadata(),
        steps=[step(1), step(2)],
        tool_results=[tool_result(1), tool_result(2)],
        final_diff="",
        test_result=TestResult(passed=[], failed=[]),
    )

    restored = TraceRecord.model_validate_json(trace.model_dump_json())

    assert restored.tool_results == [tool_result(1), tool_result(2)]


def test_trace_rejects_explicit_tool_result_count_mismatch() -> None:
    with pytest.raises(ValidationError, match="pair with every trace step"):
        TraceRecord(
            task_id="SIEVE-T1",
            run_id=uuid4(),
            run_type="baseline",
            intervention=InterventionMetadata(),
            steps=[step()],
            tool_results=[],
            final_diff="",
            test_result=TestResult(passed=[], failed=[]),
        )


def test_tool_result_record_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ToolResultRecord.model_validate(
            {**tool_result().model_dump(), "unexpected": "field"}
        )


def test_legacy_phase1_trace_without_tool_results_validates() -> None:
    fixture = "tests/fixtures/phase1/SIEVE-T1-baseline-trace.json"

    trace = TraceRecord.model_validate_json(open(fixture, encoding="utf-8").read())

    assert len(trace.steps) == 2
    assert trace.tool_results == []
