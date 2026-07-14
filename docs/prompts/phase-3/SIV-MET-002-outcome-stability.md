# SIV-MET-002 — Outcome stability comparison

## Traceability

- Phase: 3 — Scoring & Diffing (SIEVE-SPEC.md §13)
- Requirement: Outcome stability comparison (§7.2)
- Wave: 1
- Depends on: Phase 2
- Unblocks: SIV-MET-003, SIV-OPS-002
- Advances DoD: supplies the boolean outcome-stability field required in each
  §5.3 score record.

## Objective

Implement the Layer 3 comparison of baseline and perturbed test outcomes. It
must determine whether the passed and failed test-ID sets are identical,
independent of list order, while rejecting structurally invalid outcome
records through the existing schema.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit its contracts, standards, and taxonomy.
- Read `TraceRecord.test_result.passed` and `TraceRecord.test_result.failed`;
  do not modify their schema or the runner.
- Use `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` for the frozen
  T1 baseline. For the missing persisted T3 baseline fixture, construct a
  real temporary baseline through the existing `TaskRunner` and
  `RecordedBackend.from_file(tasks/SIEVE-T3/recorded_run.json)`; do not
  fabricate a `TestResult` or add a new fixture in this prompt.
- SIV-MET-003 will validate trace-pair provenance and persist the resulting
  score. This prompt supplies only the reusable comparison.
- This requirement has no §15-specific risk. It guards the interpretation
  that stable tests mean the observed pass/fail set did not change.

## Interface specification

```python
# src/sieve/outcomes.py
def outcome_stable(baseline: TestResult, perturbed: TestResult) -> bool:
    pass
```

Return `True` exactly when both
`set(baseline.passed) == set(perturbed.passed)` and
`set(baseline.failed) == set(perturbed.failed)`. Inputs are already
`TestResult` values, whose schema rejects duplicate IDs and overlap. Do not
compare process output, test order, timestamps, or tool-result text.

## Files to create or modify

- **Reads:** `SIEVE-SPEC.md` — §7.2 outcome-stability definition.
- **Reads:** `src/sieve/schemas.py` — existing `TestResult` validation.
- **Reads:** `src/sieve/agent.py` — `RecordedBackend.from_file` for
  deterministic T3 baseline construction.
- **Reads:** `src/sieve/runner.py` — production `TaskRunner` used to
  obtain the T3 baseline trace in the integration test.
- **Reads:** `tasks/SIEVE-T3/recorded_run.json` — recorded T3 baseline
  trajectory; this is the source of evidence, not a trace-record fixture.
- **Reads:** `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` —
  frozen T1 baseline trace.
- **Reads:** `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json` —
  frozen T1 stable-outcome counterpart.
- **Reads:** `tests/fixtures/phase2/SIEVE-T3-int02-perturbed-trace.json` —
  frozen T3 changed-outcome counterpart.
- **Writes (creates or modifies):** `src/sieve/outcomes.py` — set-equality
  comparison.
- **Writes (creates or modifies):** `tests/test_outcomes.py` — exact set
  equality and trace-fixture integration tests.

## Implementation notes

The binding text is: “Boolean: `true` if the perturbed run's
`test_result.passed`/`failed` sets are identical to baseline's.” Preserve
that meaning precisely: an empty pass/fail set is a valid set, reordered IDs
remain stable, and moving an ID from passed to failed is unstable.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_same_pass_fail_sets_are_stable`; `test_reordered_test_ids_are_stable`; `test_moved_test_id_from_passed_to_failed_is_unstable`; `test_added_or_removed_test_id_is_unstable`. |
| Integration | `test_phase2_trace_records_feed_outcome_stability_without_raw_output_comparison` parses the frozen T1 baseline/INT-01 pair, creates a temporary T3 baseline through `TaskRunner(ROOT, tmp_path / "runs").run("SIEVE-T3", RecordedBackend.from_file(ROOT / "tasks/SIEVE-T3/recorded_run.json"))`, then parses the frozen T3 INT-02 perturbed trace. Assert T1 is stable and T3 is unstable without comparing raw command output. |
| System | N/A — full trace-pair scoring and artifact persistence are owned by SIV-MET-003. |
| Acceptance | N/A — the Phase 3 DoD is asserted through the CLI by SIV-MET-003. |
| Smoke | `test_outcome_stability_smoke_one_passing_id` compares two one-test passing `TestResult` values and returns `True`. |
| Sanity | `test_outcome_stability_is_boolean_for_empty_equal_and_different_sets` asserts a bool result for each legal set shape. |
| Regression | N/A — SIV-OPS-002 freezes known pair outcomes as regression artifacts. |
| End-to-end | N/A — this function adds no CLI command; SIV-MET-003 owns `sieve score`. |
| API | N/A — test-result set comparison makes no API request. |
| UI | N/A — score presentation is Phase 4 scope. |

## Definition of done for this prompt

- [ ] `outcome_stable` implements §7.2 set equality without depending on
  ordering or raw command output.
- [ ] All non-N/A tests pass via `python -m pytest -v`.
- [ ] `python -m ruff check .`, `python -m black --check .`, and
  `python -m mypy --strict .` pass.
- [ ] No §5 data contract is changed.
- [ ] The module is importable by SIV-MET-003 without circular imports.
