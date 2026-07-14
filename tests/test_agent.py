from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from sieve import agent
from sieve.agent import (
    AgentTurn,
    OpenAIResponsesBackend,
    RecordedBackend,
    ToolInvocation,
    response_tools,
)
from sieve.schemas import PlannedAction, StructuredReasoningStep


def test_recorded_backend_parses_t1_turns() -> None:
    backend = RecordedBackend.from_file(Path("tasks/SIEVE-T1/recorded_run.json"))
    turn = backend.next_turn("task", [])
    assert turn is not None
    assert turn.step.planned_action == PlannedAction.EDIT_FILE
    assert turn.action.content is not None


def test_response_tools_include_structured_step_and_coding_actions() -> None:
    names = {tool["name"] for tool in response_tools()}
    assert {
        "emit_step",
        "read_file",
        "edit_file",
        "run_tests",
        "run_command",
        "search",
    } <= names


def test_agent_turn_rejects_mismatched_action() -> None:
    step = StructuredReasoningStep(
        step_id="TSIEVE-T1-S001",
        claim="claim",
        constraint="constraint",
        hypothesis="hypothesis",
        planned_action=PlannedAction.READ_FILE,
        action_target="src/file.ts",
        success_criterion="criterion",
    )
    with pytest.raises(ValidationError, match="planned_action"):
        AgentTurn(
            step=step,
            action=ToolInvocation(name=PlannedAction.SEARCH, target="src/file.ts"),
        )


def test_agent_turn_requires_edit_content() -> None:
    step = StructuredReasoningStep(
        step_id="TSIEVE-T1-S001",
        claim="claim",
        constraint="constraint",
        hypothesis="hypothesis",
        planned_action=PlannedAction.EDIT_FILE,
        action_target="src/file.ts",
        success_criterion="criterion",
    )
    with pytest.raises(ValidationError, match="replacement content"):
        AgentTurn(
            step=step,
            action=ToolInvocation(name=PlannedAction.EDIT_FILE, target="src/file.ts"),
        )


class FakeOpenAI:
    def __init__(self, output: Sequence[object]) -> None:
        self.responses = SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(output=output, request=kwargs)
        )


def test_live_backend_parses_valid_structured_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = [
        SimpleNamespace(
            type="function_call",
            name="emit_step",
            arguments=(
                '{"step_id":"TSIEVE-T1-S001","claim":"claim",'
                '"constraint":"constraint","hypothesis":"hypothesis",'
                '"planned_action":"read_file","action_target":"src/file.ts",'
                '"success_criterion":"criterion"}'
            ),
        ),
        SimpleNamespace(
            type="function_call",
            name="read_file",
            arguments='{"target":"src/file.ts"}',
        ),
    ]
    monkeypatch.setattr(agent, "OpenAI", lambda: FakeOpenAI(output))
    turn = OpenAIResponsesBackend("test-model").next_turn("task", [])
    assert turn is not None
    assert turn.action.name == PlannedAction.READ_FILE


def test_live_backend_rejects_action_without_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = [
        SimpleNamespace(
            type="function_call",
            name="read_file",
            arguments='{"target":"src/file.ts"}',
        )
    ]
    monkeypatch.setattr(agent, "OpenAI", lambda: FakeOpenAI(output))
    with pytest.raises(ValueError, match="without emit_step"):
        OpenAIResponsesBackend("test-model").next_turn("task", [])


def test_live_backend_returns_none_without_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent, "OpenAI", lambda: FakeOpenAI([]))
    assert OpenAIResponsesBackend("test-model").next_turn("task", []) is None
