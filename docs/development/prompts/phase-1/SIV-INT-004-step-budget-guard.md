# SIV-INT-004 — Step budget guard

## Traceability
- Phase: 1 — Resume & Replay (SIEVE-SPEC.md §13)
- Requirement: Step budget guard: resumption halts after N steps to bound cost/time
- Wave: 1
- Depends on: none
- Unblocks: SIV-INT-002
- Advances DoD: bounds the resumption path required to perform the no-op replay safely.

## Objective

Create a small, Layer 2 budget primitive that a resumed run can use to permit at most N newly generated steps and fail deterministically before an N+1st generation. It must be independent of the Phase 0 runner’s baseline `max_steps` loop, which has a different lifecycle and must remain unchanged.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- This module reads no persisted §5 contract and writes no trace field; SIV-INT-002 will use it while producing a valid §5.2 replay output.
- No prior Phase 1 prompt is assumed. SIV-INT-002 will import this guard.
- Risk: “Resumption produces incoherent continuations.” A finite, explicit guard prevents an incoherent continuation from consuming unbounded API calls or time.

## Interface specification

```python
# src/sieve/budget.py
class StepBudgetExceeded(RuntimeError):
    """Raised before a resumption attempts to exceed its new-step budget."""

class StepBudget:
    def __init__(self, maximum_steps: int) -> None:
        """Validate and initialize a resumption-only step budget."""
    @property
    def consumed_steps(self) -> int:
        """Return the number of newly generated steps consumed."""
    @property
    def remaining_steps(self) -> int:
        """Return the number of newly generated steps still permitted."""
    def consume(self) -> None:
        """Consume one step or raise StepBudgetExceeded without incrementing."""
```

`maximum_steps` must be a positive integer; zero, negative values, booleans, and non-integers raise `ValueError`. `consume()` may be called exactly `maximum_steps` times; on the next call it raises `StepBudgetExceeded` and leaves both counters unchanged.

## Files to create or modify

- **Reads:** `src/sieve/runner.py` — retain the Phase 0 baseline-run step-limit semantics without modifying them.
- **Writes (creates or modifies):** `src/sieve/budget.py` — the independent resumption budget primitive.
- **Writes (creates or modifies):** `tests/test_budget.py` — deterministic budget tests.

## Implementation notes

The exact binding rule is: “generation resumes at step `k` and proceeds until the agent signals task completion or a step budget is exhausted (SIV-INT-004 defines the budget).” Count only generation attempts made after resumption; replayed fixed context is not generated work and must not consume this budget. Do not select a global default in this module; SIV-INT-002 exposes the default at the resume interface.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_step_budget_allows_exactly_maximum_steps_then_raises`: maximum 2 permits two consumes, then raises with counters unchanged. `test_step_budget_rejects_zero_negative_boolean_and_non_integer_limits`. |
| Integration | N/A — the guard has no layer boundary until SIV-INT-002 integrates it into the resume runner. |
| System | N/A — the guard alone neither invokes a backend nor produces a trace; SIV-INT-002 covers resumed-run system behavior. |
| Acceptance | N/A — Phase 1 no-op replay acceptance is owned by SIV-INT-003. |
| Smoke | `test_step_budget_smoke_one_step_limit`: a maximum of one has one remaining step, consumes it, then reports zero. |
| Sanity | `test_normal_length_budget_has_remaining_capacity`: a budget of 20 accepts the two generated turns in the recorded SIEVE-T1 trajectory without raising. |
| Regression | N/A — a pure counter has no recorded trace output; replay regression belongs to SIV-INT-003. |
| End-to-end | N/A — no CLI is added by this primitive; SIV-INT-002 adds and tests the resume command. |
| API | N/A — the primitive makes no API request; API replay-call shape is owned by SIV-INT-002. |
| UI | N/A — Phase 1 has no report artifact. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_budget.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new or modified files.
- [ ] No data contract in §5 was altered; this prompt creates no persisted data.
- [ ] No golden or regression fixture is authored by this prompt.
