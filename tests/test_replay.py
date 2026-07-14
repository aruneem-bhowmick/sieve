"""Tests for fixed-context reconstruction used by Phase 1 resumption."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

from sieve.replay import ReplayContextItem, build_replay_context
from sieve.schemas import (
    InterventionMetadata,
    PlannedAction,
    StructuredReasoningStep,
    TestResult,
    TraceRecord,
)


def _step(number: int) -> StructuredReasoningStep:
    return StructuredReasoningStep(
        step_id=f"TSIEVE-T1-S{number:03d}",
        claim=f"claim {number}",
        constraint=f"constraint {number}",
        hypothesis=f"hypothesis {number}",
        planned_action=PlannedAction.READ_FILE,
        action_target=f"src/file-{number}.ts",
        success_criterion=f"criterion {number}",
    )


def _trace(*steps: StructuredReasoningStep) -> TraceRecord:
    return TraceRecord(
        task_id="SIEVE-T1",
        run_id=uuid4(),
        run_type="baseline",
        intervention=InterventionMetadata(),
        steps=list(steps),
        final_diff="",
        test_result=TestResult(passed=[], failed=[]),
    )


def test_build_replay_context_serializes_only_prior_steps_in_order() -> None:
    trace = _trace(_step(1), _step(2), _step(3))

    context = build_replay_context(trace, "TSIEVE-T1-S003")

    assert context == [
        ReplayContextItem("TSIEVE-T1-S001", trace.steps[0].model_dump_json()),
        ReplayContextItem("TSIEVE-T1-S002", trace.steps[1].model_dump_json()),
    ]


def test_build_replay_context_excludes_target_and_later_steps() -> None:
    trace = _trace(_step(1), _step(2), _step(3))

    context = build_replay_context(trace, "TSIEVE-T1-S002")

    assert [item.step_id for item in context] == ["TSIEVE-T1-S001"]


def test_build_replay_context_rejects_unknown_target_step() -> None:
    with pytest.raises(ValueError, match="not present"):
        build_replay_context(_trace(_step(1)), "TSIEVE-T1-S404")


def test_replay_context_accepts_phase0_trace_record() -> None:
    raw_recording = json.loads(
        (Path.cwd() / "tasks/SIEVE-T1/recorded_run.json").read_text(encoding="utf-8")
    )
    trace = _trace(
        *[
            StructuredReasoningStep.model_validate(turn["step"])
            for turn in raw_recording["turns"]
        ]
    )

    context = build_replay_context(trace, "TSIEVE-T1-S002")

    assert context == [
        ReplayContextItem("TSIEVE-T1-S001", trace.steps[0].model_dump_json())
    ]


def test_build_replay_context_smoke_single_prior_step() -> None:
    context = build_replay_context(_trace(_step(1), _step(2)), "TSIEVE-T1-S002")

    assert len(context) == 1


def test_replay_context_is_deterministic_and_immutable() -> None:
    trace = _trace(_step(1), _step(2))

    first = build_replay_context(trace, "TSIEVE-T1-S002")
    second = build_replay_context(trace, "TSIEVE-T1-S002")

    assert first == second
    mutable_item = cast(Any, first[0])
    with pytest.raises(FrozenInstanceError):
        mutable_item.content = "changed"
    assert trace.steps[0].claim == "claim 1"
