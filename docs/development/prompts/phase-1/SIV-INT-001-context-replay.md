# SIV-INT-001 — Context replay

## Traceability
- Phase: 1 — Resume & Replay (SIEVE-SPEC.md §13)
- Requirement: Context replay: reconstruct prior steps as fixed conversational context for the API
- Wave: 1
- Depends on: none
- Unblocks: SIV-INT-002
- Advances DoD: supplies the verbatim steps `1..k-1` required before a no-op resume can reproduce the baseline final diff.

## Objective

Create the Layer 2 pure context-assembly boundary. Given a validated baseline `TraceRecord` and a target step ID, it must reconstruct every earlier structured step as immutable, deterministic API context in ascending order, without changing a trace, invoking an agent, or implementing an intervention.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read `TraceRecord.steps`, `StructuredReasoningStep.step_id`, `claim`, `constraint`, `hypothesis`, `planned_action`, `action_target`, and `success_criterion`; do not write or alter any §5 field.
- No prior Phase 1 prompt is assumed. `SIV-INT-002` will consume this module.
- Risk: “Resumption produces incoherent continuations.” Preserve prior context verbatim and in chronological order so SIV-INT-003 can isolate model replay fidelity from context corruption.

## Interface specification

```python
# src/sieve/replay.py
from dataclasses import dataclass
from sieve.schemas import TraceRecord

@dataclass(frozen=True)
class ReplayContextItem:
    step_id: str
    content: str

def build_replay_context(trace: TraceRecord, target_step_id: str) -> list[ReplayContextItem]:
    """Return JSON-serialized §5.1 steps strictly before target_step_id."""
```

`content` must be `StructuredReasoningStep.model_dump_json()` for the source step, with no wrapper prose and no field omission. Raise `ValueError` when `target_step_id` is not in `trace.steps`. The target step itself and later steps must not appear in the result.

## Files to create or modify

- **Reads:** `src/sieve/schemas.py` — validate the existing §5.1/§5.2 models and serialization API.
- **Reads:** `tests/test_schemas.py` — follow existing fixture construction and validation style.
- **Writes (creates or modifies):** `src/sieve/replay.py` — `ReplayContextItem` and `build_replay_context`.
- **Writes (creates or modifies):** `tests/test_replay.py` — focused context-assembly tests.

## Implementation notes

The binding mechanic is: “steps `1..k-1` are replayed as fixed context verbatim.” Treat a step ID as the boundary, not a numeric index supplied by a caller. Return a new list of frozen values so a caller cannot mutate stored trace objects through the result. This prompt must not add `tool_results` to the locked trace shape; SIV-SCH-002 owns raw tool-call pairing in Phase 2.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_build_replay_context_serializes_only_prior_steps_in_order`: a three-step `SIEVE-T1` trace targeted at `TSIEVE-T1-S003` returns exact JSON for S001 then S002. `test_build_replay_context_excludes_target_and_later_steps`: target S002 returns only S001. `test_build_replay_context_rejects_unknown_target_step`: assert `ValueError`. |
| Integration | `test_replay_context_accepts_phase0_trace_record`: load `tasks/SIEVE-T1/recorded_run.json` turns into a valid `TraceRecord`, build context for S002, and assert the result has S001’s exact §5.1 JSON. |
| System | N/A — this pure reconstruction component neither invokes a backend nor executes a complete task pipeline; SIV-INT-002 owns resumed-run system coverage. |
| Acceptance | N/A — the Phase 1 DoD is exercised by the no-op fidelity acceptance test in SIV-INT-003 after resumption exists. |
| Smoke | `test_build_replay_context_smoke_single_prior_step`: build context for S002 from a two-step trace and assert one item is returned. |
| Sanity | `test_replay_context_is_deterministic_and_immutable`: two calls have equal values, returned items are frozen, and no source `TraceRecord` field changes. |
| Regression | N/A — no golden replay outcome exists until SIV-INT-002 can generate a resumed trace; SIV-INT-003 owns the Phase 1 golden regression. |
| End-to-end | N/A — this module adds no CLI surface; the `sieve resume` path is introduced and tested by SIV-INT-002. |
| API | N/A — this module prepares API context but does not call or configure the Codex/GPT-5.6 wrapper; SIV-INT-002 tests the mocked resumption call shape. |
| UI | N/A — Phase 1 creates no static HTML report; report UI begins in Phase 4. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_replay.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new or modified files.
- [ ] No data contract in §5 was altered; this module only serializes existing fields.
- [ ] No golden or regression fixture is authored by this prompt.
