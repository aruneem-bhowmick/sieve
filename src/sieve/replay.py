"""Pure reconstruction of fixed prior-step context for Layer 2 replay."""

from __future__ import annotations

from dataclasses import dataclass

from sieve.schemas import TraceRecord


@dataclass(frozen=True)
class ReplayContextItem:
    """An immutable, serialized reasoning step supplied as replay context."""

    step_id: str
    content: str


def build_replay_context(
    trace: TraceRecord, target_step_id: str
) -> list[ReplayContextItem]:
    """Return JSON-serialized §5.1 steps strictly before ``target_step_id``.

    The target is identified by its recorded step ID so callers cannot replay a
    numeric position that disagrees with the trace.  Each item is newly created
    and holds the exact Pydantic JSON serialization of the original step.
    """
    for index, step in enumerate(trace.steps):
        if step.step_id == target_step_id:
            return [
                ReplayContextItem(
                    step_id=previous_step.step_id,
                    content=previous_step.model_dump_json(),
                )
                for previous_step in trace.steps[:index]
            ]
    raise ValueError(f"target step ID is not present in trace: {target_step_id}")
