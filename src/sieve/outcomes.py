"""Outcome comparison for baseline and perturbed trace results."""

from __future__ import annotations

from sieve.schemas import TestResult


def outcome_stable(baseline: TestResult, perturbed: TestResult) -> bool:
    """Return whether the two traces have identical pass and failure ID sets."""

    return set(baseline.passed) == set(perturbed.passed) and set(
        baseline.failed
    ) == set(perturbed.failed)
