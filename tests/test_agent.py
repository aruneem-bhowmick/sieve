from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
from sieve.replay import ReplayContextItem
from sieve.schemas import PlannedAction, StructuredReasoningStep, ToolResultRecord


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
        self._output = output
        self.request: dict[str, Any] | None = None
        self.responses = SimpleNamespace(create=self.create)

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(output=self._output)


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


def test_openai_resume_turn_sends_fixed_context_before_history_and_uses_response_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = [
        SimpleNamespace(
            type="function_call",
            name="emit_step",
            arguments=(
                '{"step_id":"TSIEVE-T1-S002","claim":"claim",'
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
    fake = FakeOpenAI(output)
    monkeypatch.setattr(agent, "OpenAI", lambda: fake)
    backend = OpenAIResponsesBackend("test-model")
    fixed = ReplayContextItem("TSIEVE-T1-S001", '{"step_id":"TSIEVE-T1-S001"}')
    turn = backend.resume_turn(
        "task",
        [fixed],
        [
            ToolResultRecord(
                name=PlannedAction.READ_FILE,
                target="task.md",
                output="contents",
                succeeded=True,
            )
        ],
    )
    assert turn is not None
    assert fake.request is not None
    request = fake.request
    contents = [item["content"] for item in request["input"]]
    assert contents.index(fixed.content) < next(
        index for index, content in enumerate(contents) if "tool_result" in content
    )
    assert request["tools"] == response_tools()


def test_recorded_backend_resume_starts_at_requested_step() -> None:
    backend = RecordedBackend.from_file_from_step(
        Path("tasks/SIEVE-T1/recorded_run.json"), "TSIEVE-T1-S002"
    )
    turn = backend.resume_turn("task", [], [])
    assert turn is not None
    assert turn.step.step_id == "TSIEVE-T1-S002"


def test_openai_history_serializes_tool_result_record_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeOpenAI([])
    monkeypatch.setattr(agent, "OpenAI", lambda: fake)
    result = ToolResultRecord(
        name=PlannedAction.RUN_TESTS,
        target="npm test",
        output="stdout\nstderr",
        succeeded=False,
    )

    assert OpenAIResponsesBackend("test-model").next_turn("task", [result]) is None
    assert fake.request is not None
    history_content = fake.request["input"][-1]["content"]
    assert '"name": "run_tests"' in history_content
    assert '"target": "npm test"' in history_content
    assert '"output": "stdout\\nstderr"' in history_content
    assert '"succeeded": false' in history_content
