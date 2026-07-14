"""Tests for the independent resumption step-budget guard."""

from __future__ import annotations

import pytest

from sieve.budget import StepBudget, StepBudgetExceeded


def test_step_budget_allows_exactly_maximum_steps_then_raises() -> None:
    """The N+1st consume fails and preserves the exhausted counters."""
    budget = StepBudget(2)

    budget.consume()
    budget.consume()

    with pytest.raises(StepBudgetExceeded):
        budget.consume()

    assert budget.consumed_steps == 2
    assert budget.remaining_steps == 0


@pytest.mark.parametrize("maximum_steps", [0, -1, True, False, 1.5, "2", None])
def test_step_budget_rejects_zero_negative_boolean_and_non_integer_limits(
    maximum_steps: object,
) -> None:
    """Only a positive non-boolean integer is a valid budget limit."""
    with pytest.raises(ValueError):
        StepBudget(maximum_steps)  # type: ignore[arg-type]


def test_step_budget_smoke_one_step_limit() -> None:
    """A one-step budget transitions from one remaining step to zero."""
    budget = StepBudget(1)

    assert budget.remaining_steps == 1
    budget.consume()
    assert budget.remaining_steps == 0


def test_normal_length_budget_has_remaining_capacity() -> None:
    """The recorded SIEVE-T1 two-turn trajectory fits within a budget of 20."""
    budget = StepBudget(20)

    budget.consume()
    budget.consume()

    assert budget.consumed_steps == 2
    assert budget.remaining_steps == 18
