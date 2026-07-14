"""Agent backends that emit a reasoning step followed by one coding action."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, model_validator

from sieve.schemas import PlannedAction, StructuredReasoningStep


class ToolInvocation(BaseModel):
    """A local coding-tool call selected by the agent."""

    model_config = ConfigDict(extra="forbid")

    name: PlannedAction
    target: str
    content: str | None = None


class AgentTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: StructuredReasoningStep
    action: ToolInvocation

    @model_validator(mode="after")
    def action_matches_plan(self) -> AgentTurn:
        """Reject actions that do not faithfully match the declared step."""
        if self.step.planned_action != self.action.name:
            raise ValueError("tool invocation must match planned_action")
        if self.step.action_target != self.action.target:
            raise ValueError("tool invocation target must match action_target")
        if self.action.name == PlannedAction.EDIT_FILE and self.action.content is None:
            raise ValueError("edit_file requires replacement content")
        return self


@dataclass(frozen=True)
class ToolResult:
    name: PlannedAction
    target: str
    output: str
    succeeded: bool


class CodingAgentBackend(Protocol):
    """Backend interface used by the runner for one agent turn at a time."""

    def next_turn(
        self, task_prompt: str, history: list[ToolResult]
    ) -> AgentTurn | None:
        """Return one validated turn or ``None`` when the task is complete."""
        ...


def _tool_schema(
    name: PlannedAction, properties: dict[str, object]
) -> dict[str, object]:
    """Build the strict Responses API schema for one local coding tool."""
    return {
        "type": "function",
        "name": name.value,
        "description": f"Perform the local {name.value} action.",
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": ["target"],
            "additionalProperties": False,
        },
        "strict": True,
    }


def response_tools() -> list[dict[str, object]]:
    """OpenAI function tools used to enforce the structured step contract."""

    step_schema = StructuredReasoningStep.model_json_schema()
    step_schema["additionalProperties"] = False
    return [
        {
            "type": "function",
            "name": "emit_step",
            "description": (
                "Emit the required structured reasoning step before an action."
            ),
            "parameters": step_schema,
            "strict": True,
        },
        _tool_schema(PlannedAction.READ_FILE, {"target": {"type": "string"}}),
        _tool_schema(
            PlannedAction.EDIT_FILE,
            {"target": {"type": "string"}, "content": {"type": "string"}},
        ),
        _tool_schema(PlannedAction.RUN_TESTS, {"target": {"type": "string"}}),
        _tool_schema(PlannedAction.RUN_COMMAND, {"target": {"type": "string"}}),
        _tool_schema(PlannedAction.SEARCH, {"target": {"type": "string"}}),
    ]


class OpenAIResponsesBackend:
    """Direct Responses API backend; only used by manual ``--live`` runs."""

    def __init__(self, model: str) -> None:
        """Create a direct Responses API backend for the requested model."""
        self._client = OpenAI()
        self._model = model

    def next_turn(
        self, task_prompt: str, history: list[ToolResult]
    ) -> AgentTurn | None:
        """Request and validate one structured reasoning/action pair."""
        input_items: list[dict[str, str]] = [
            {
                "role": "developer",
                "content": (
                    "You are completing a coding task. Before each action call "
                    "emit_step, "
                    "then call exactly one matching local coding tool. Return no prose."
                ),
            },
            {"role": "user", "content": task_prompt},
        ]
        input_items.extend(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "tool_result": {
                            "name": result.name.value,
                            "target": result.target,
                            "succeeded": result.succeeded,
                            "output": result.output,
                        }
                    }
                ),
            }
            for result in history
        )
        response = self._client.responses.create(
            model=self._model,
            input=cast(Any, input_items),
            tools=cast(Any, response_tools()),
        )
        calls: dict[str, dict[str, Any]] = {}
        for item in response.output:
            if item.type == "function_call":
                calls[item.name] = json.loads(item.arguments)
        if not calls:
            return None
        if "emit_step" not in calls:
            raise ValueError("model returned an action without emit_step")
        action_calls = [name for name in calls if name != "emit_step"]
        if len(action_calls) != 1:
            raise ValueError("model must return exactly one coding action")
        action_name = action_calls[0]
        action = calls[action_name]
        return AgentTurn(
            step=StructuredReasoningStep.model_validate(calls["emit_step"]),
            action=ToolInvocation(name=PlannedAction(action_name), **action),
        )


class RecordedBackend:
    """Deterministic local backend used by tests, CI, and the default CLI path."""

    def __init__(self, turns: list[AgentTurn]) -> None:
        """Create a deterministic backend over a fixed sequence of turns."""
        self._turns = turns
        self._position = 0

    @classmethod
    def from_file(cls, path: Path) -> RecordedBackend:
        """Load validated recorded turns from a fixture JSON document."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([AgentTurn.model_validate(turn) for turn in raw["turns"]])

    def next_turn(
        self, task_prompt: str, history: list[ToolResult]
    ) -> AgentTurn | None:
        """Return the next recorded turn, or completion when the sequence ends."""
        del task_prompt, history
        if self._position >= len(self._turns):
            return None
        turn = self._turns[self._position]
        self._position += 1
        return turn
