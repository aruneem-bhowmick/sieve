# SIV-INT-003 — No-op intervention fidelity check

## Traceability
- Phase: 1 — Resume & Replay (SIEVE-SPEC.md §13)
- Requirement: No-op intervention fidelity check (the DoD above, as an automated test)
- Wave: 3
- Depends on: SIV-INT-002
- Unblocks: none
- Advances DoD: is the automated proof that resuming the completed SIEVE-T1 baseline from its own step 2, with no edited field, reproduces its original final diff.

## Objective

Add the isolated Phase 1 acceptance and golden-regression proof. It must establish a completed SIEVE-T1 baseline run with its additive S001 workspace checkpoint, resume that baseline at `TSIEVE-T1-S002` through the production `ResumeRunner` with a deterministic recorded backend, and assert exact final-diff equality against a frozen baseline trace. This is the phase gate, not a weaker unit test of a helper.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read the §5.2 baseline trace `task_id`, `run_id`, `run_type`, `intervention`, `steps`, `final_diff`, and `test_result`, plus the additive baseline filesystem checkpoint at `checkpoints/TSIEVE-T1-S001/`. The expected and replay traces retain the locked shape and use empty intervention metadata.
- SIV-INT-002 has delivered `ResumeRunner`, the `sieve resume` CLI, and `tasks/SIEVE-T1/recorded_resume_run.json`.
- Risk: “Resumption produces incoherent continuations.” Compare the actual final diff from a clean resumed execution to a frozen baseline, not trace prose or test output alone.

## Interface specification

```python
# tests/fixtures/phase1/SIEVE-T1-baseline-trace.json
# A valid completed §5.2 baseline trace with target step_id "TSIEVE-T1-S002".

# tests/test_no_op_fidelity.py
def test_phase_1_no_op_resume_from_step_2_reproduces_baseline_final_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Assert exact final-diff equality for the frozen no-op replay."""
```

The fixture’s `final_diff` must be the expected unified diff produced by the Phase 0 recorded SIEVE-T1 baseline. The test must create its temporary completed baseline through `TaskRunner`, validate the checkpoint `checkpoints/TSIEVE-T1-S001/`, use `ResumeRunner.resume` with that temporary run directory, target exactly `TSIEVE-T1-S002`, make no reasoning-field mutation, mock the task test subprocess deterministically, and require both the generated baseline and resumed final diffs to equal the frozen fixture final diff.

## Files to create or modify

- **Reads:** `src/sieve/resume.py` — execute the production resume path from SIV-INT-002.
- **Reads:** `src/sieve/runner.py` — create the complete baseline run and its S001 checkpoint through the production runner.
- **Reads:** `src/sieve/schemas.py` — validate the frozen §5.2 baseline fixture.
- **Reads:** `tasks/SIEVE-T1/recorded_resume_run.json` — deterministic regenerated suffix beginning at S002.
- **Reads:** `tasks/SIEVE-T1/recorded_run.json` — validate the fixture’s Phase 0 baseline provenance.
- **Writes (creates or modifies):** `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` — frozen valid baseline trace and expected final diff.
- **Writes (creates or modifies):** `tests/test_no_op_fidelity.py` — acceptance, regression, smoke, and CLI fidelity checks.

## Implementation notes

The Phase DoD is exact: “Resuming a completed baseline trace from its own step 2 (no field edited — a no-op intervention) reproduces the original trace's final diff, proving replay fidelity.” Therefore use exact string equality, not the Phase 3 AST tolerance, score, or a prose comparison. Assert that the replay produces a distinct run ID and directory while keeping `run_type="baseline"` and every `intervention` member null. A mismatch is a Phase 1 failure even if task tests pass.

Do not modify application source, CLI source, data contracts, or the Phase 0 fixture in this prompt. If the test reveals a product defect, report it to the ideator and replan the relevant SIV-INT-002 prompt rather than making an undeclared repair.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_frozen_phase1_baseline_trace_validates_as_trace_record`: parse the fixture with `TraceRecord.model_validate_json`, assert S002 exists and intervention fields are all null. |
| Integration | `test_no_op_fidelity_uses_production_runner_and_resume_runner`: spy on the production baseline and resume boundaries and assert the S001 checkpoint, S002 target, and recorded backend are supplied. |
| System | `test_no_op_resume_executes_complete_sieve_t1_path`: with mocked Vitest, assert the resumed workspace executes the regenerated S002 test action and yields a complete valid trace. |
| Acceptance | `test_phase_1_no_op_resume_from_step_2_reproduces_baseline_final_diff`: assert exact equality of baseline and resumed `final_diff`, no mutation of claim/constraint/hypothesis, distinct run IDs, and a written replay trace. |
| Smoke | `test_no_op_fidelity_smoke`: run the same S002 no-op replay through recorded fixtures and assert it completes and writes `trace.json`. |
| Sanity | `test_no_op_fidelity_has_nonempty_equal_diffs_and_green_recorded_test_result`: assert both diff strings are non-empty and equal, and the deterministic test result has no failures. |
| Regression | `test_phase1_golden_baseline_diff_remains_equal_after_no_op_replay`: CI loads `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` and asserts exact final-diff equality without a live API call. |
| End-to-end | `test_cli_no_op_resume_from_step_2_matches_fixture_diff`: invoke `sieve run --task SIEVE-T1 --runs-dir` with a temporary directory, parse the baseline run directory, invoke `sieve resume --baseline-run-dir` with that exact directory and target S002, parse its emitted trace path, and assert the saved final diff equals the frozen fixture. |
| API | N/A — this acceptance gate uses the recorded backend so CI is deterministic; mocked API resumption request formation is covered by SIV-INT-002 and live API calls remain manual only. |
| UI | N/A — Phase 1 produces no static report, so no report UI exists to render. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_no_op_fidelity.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new or modified files.
- [ ] No data contract in §5 was altered; the golden fixture is a valid existing §5.2 shape.
- [ ] The frozen baseline fixture is committed with the test that characterizes it.
