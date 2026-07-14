"""Stable data contracts for Sieve traces."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlannedAction(StrEnum):
    READ_FILE = "read_file"
    EDIT_FILE = "edit_file"
    RUN_TESTS = "run_tests"
    RUN_COMMAND = "run_command"
    SEARCH = "search"


class StructuredReasoningStep(BaseModel):
    """The §5.1 reasoning object emitted before each coding action."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(pattern=r"^T.+-S\d{3,}$")
    claim: str
    constraint: str
    hypothesis: str
    planned_action: PlannedAction
    action_target: str
    success_criterion: str


class InterventionMetadata(BaseModel):
    """The §5.2 intervention descriptor; Phase 0 writes baseline values."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["INT-01", "INT-02", "INT-03"] | None = None
    target_step_id: str | None = None
    target_field: Literal["claim", "constraint", "hypothesis"] | None = None
    original_value: str | None = None
    replacement_value: str | None = None


class TestResult(BaseModel):
    __test__ = False

    model_config = ConfigDict(extra="forbid")

    passed: list[str]
    failed: list[str]

    @field_validator("passed", "failed")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        """Ensure each outcome list names a test at most once."""
        if len(value) != len(set(value)):
            raise ValueError("test identifiers must be unique")
        return value

    @model_validator(mode="after")
    def disjoint_sets(self) -> TestResult:
        """Ensure no test is reported as both passing and failing."""
        if set(self.passed) & set(self.failed):
            raise ValueError("a test cannot both pass and fail")
        return self


class TraceRecord(BaseModel):
    """The Phase 0 §5.2 trace record persisted as ``trace.json``."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    run_id: UUID
    run_type: Literal["baseline", "perturbed"]
    intervention: InterventionMetadata
    steps: list[StructuredReasoningStep]
    final_diff: str
    test_result: TestResult
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_step_order(self) -> TraceRecord:
        """Validate task-local step ownership and increasing step identifiers."""
        prefix = f"T{self.task_id}-S"
        numbers: list[int] = []
        for step in self.steps:
            if not step.step_id.startswith(prefix):
                raise ValueError("step_id must belong to the trace task")
            numbers.append(int(step.step_id.removeprefix(prefix)))
        if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
            raise ValueError("step_ids must be monotonically increasing per task")
        if self.run_type == "baseline" and any(
            value is not None
            for value in (
                self.intervention.type,
                self.intervention.target_step_id,
                self.intervention.target_field,
                self.intervention.original_value,
                self.intervention.replacement_value,
            )
        ):
            raise ValueError("baseline traces must not contain an intervention")
        return self
