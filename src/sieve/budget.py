"""Step-budget guard for resumed agent executions."""

from __future__ import annotations


class StepBudgetExceeded(RuntimeError):
    """Raised before a resumption attempts to exceed its new-step budget."""


class StepBudget:
    """Track the newly generated steps allowed during one resumption."""

    def __init__(self, maximum_steps: int) -> None:
        """Validate and initialize a resumption-only step budget."""
        if isinstance(maximum_steps, bool) or not isinstance(maximum_steps, int):
            raise ValueError("maximum_steps must be a positive integer")
        if maximum_steps <= 0:
            raise ValueError("maximum_steps must be a positive integer")
        self._maximum_steps = maximum_steps
        self._consumed_steps = 0

    @property
    def consumed_steps(self) -> int:
        """Return the number of newly generated steps consumed."""
        return self._consumed_steps

    @property
    def remaining_steps(self) -> int:
        """Return the number of newly generated steps still permitted."""
        return self._maximum_steps - self._consumed_steps

    def consume(self) -> None:
        """Consume one step or raise StepBudgetExceeded without incrementing."""
        if self._consumed_steps == self._maximum_steps:
            raise StepBudgetExceeded("resumption step budget exhausted")
        self._consumed_steps += 1
