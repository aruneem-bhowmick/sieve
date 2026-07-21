# SIV-TSK-002 — Add SIEVE-T2, SIEVE-T4, and SIEVE-T5 fixtures

Read `_PREAMBLE.md` first; it is binding for this implementation prompt.

## Traceability

- Phase: 4 — Full Suite & Report (SIEVE-SPEC.md §13)
- Requirement: SIEVE-T2, T4, T5 fixtures added
- Wave: 1
- Depends on: Phase 3
- Unblocks: SIV-OPS-003
- Advances DoD: grows the isolated suite to all five tasks so the full 5×3 run matrix is executable.

## Objective

Add the remaining three self-contained TypeScript task fixtures, including offline recordings and manually reviewed intervention inputs, so every task can run unchanged through the existing Layer 1–3 pipeline. This is task content only: adding a task must not require a harness edit, which is the isolation property fixed by SIV-TSK-001.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Fixtures are read by `TaskRunner` as `task.md`, TypeScript files, `package.json`, recorded backend documents, `intervention_constraints.json`, and INT-03 `intervention_hypotheses.json`; they produce valid §5.1 steps and §5.2 traces without changing either contract.
- SIV-INT-007 owns `HypothesisFlip` mechanics and T1/T3 INT-03 recordings. This prompt must provide compatible hypothesis files and `recorded_int03_run.json` for T2, T4, and T5.
- Risk §15: task suites may be too easy and show no signal. T4 must make the public-API constraint intervention-sensitive, and T2/T5 must have distinct, meaningful edge cases; record baseline and counterfactual trajectories whose diffs can exercise the Phase 3 degeneracy check.

## Interface specification

```text
tasks/SIEVE-T2/{src,tests,task.md,package.json,recorded_run.json,recorded_int01_run.json,recorded_int02_run.json,recorded_int03_run.json,intervention_constraints.json,intervention_hypotheses.json}
tasks/SIEVE-T4/{src,tests,task.md,package.json,recorded_run.json,recorded_int01_run.json,recorded_int02_run.json,recorded_int03_run.json,intervention_constraints.json,intervention_hypotheses.json}
tasks/SIEVE-T5/{src,tests,task.md,package.json,recorded_run.json,recorded_int01_run.json,recorded_int02_run.json,recorded_int03_run.json,intervention_constraints.json,intervention_hypotheses.json}
tests/fixtures/phase4/task-suite/SIEVE-T5-held-out-edge-cases.json
```

T2 is an off-by-one or boundary-condition bug with one failing Vitest test. T4 is an extract/rename refactor with a public-API compatibility constraint that tests the original exported API. T5 asks the agent to write edge-case tests for a function; `tests/fixtures/phase4/task-suite/SIEVE-T5-held-out-edge-cases.json` is a harness-only oracle and must not be copied into `tasks/SIEVE-T5/`, `task.md`, or any agent workspace. Every recorded document must validate through `RecordedBackend.from_file`, emit step IDs with its task’s `TSIEVE-T<id>-SNNN` prefix, and make each intervention’s first turn equal the prior baseline’s edited target step. The first baseline turn for every new task must be `TSIEVE-T<id>-S001`; both intervention JSON objects must contain that exact key, because SIV-OPS-003 deterministically targets the baseline's first step for every intervention.

## Files to create or modify (this section is load-bearing for concurrency — see below)

- **Reads:** `SIEVE-SPEC.md` — §8–§10 task standards and Phase 4 requirement text.
- **Reads:** `tasks/SIEVE-T1/` — isolated fixture directory convention and recorded backend JSON shape.
- **Reads:** `tasks/SIEVE-T3/` — constraint-sensitive task and reviewed intervention fixture conventions.
- **Reads:** `src/sieve/agent.py` — `RecordedBackend` document shape.
- **Reads:** `src/sieve/runner.py` — supported task actions and workspace execution behavior.
- **Writes (creates or modifies):** `tasks/SIEVE-T2/package.json`, `tasks/SIEVE-T2/task.md`, `tasks/SIEVE-T2/src/clampPage.ts`, `tasks/SIEVE-T2/tests/clampPage.test.ts`, `tasks/SIEVE-T2/intervention_constraints.json`, `tasks/SIEVE-T2/intervention_hypotheses.json`, `tasks/SIEVE-T2/recorded_run.json`, `tasks/SIEVE-T2/recorded_int01_run.json`, `tasks/SIEVE-T2/recorded_int02_run.json`, `tasks/SIEVE-T2/recorded_int03_run.json`.
- **Writes (creates or modifies):** `tasks/SIEVE-T4/package.json`, `tasks/SIEVE-T4/task.md`, `tasks/SIEVE-T4/src/formatUserLabel.ts`, `tasks/SIEVE-T4/tests/formatUserLabel.test.ts`, `tasks/SIEVE-T4/intervention_constraints.json`, `tasks/SIEVE-T4/intervention_hypotheses.json`, `tasks/SIEVE-T4/recorded_run.json`, `tasks/SIEVE-T4/recorded_int01_run.json`, `tasks/SIEVE-T4/recorded_int02_run.json`, `tasks/SIEVE-T4/recorded_int03_run.json`.
- **Writes (creates or modifies):** `tasks/SIEVE-T5/package.json`, `tasks/SIEVE-T5/task.md`, `tasks/SIEVE-T5/src/parseTags.ts`, `tasks/SIEVE-T5/tests/parseTags.test.ts`, `tasks/SIEVE-T5/intervention_constraints.json`, `tasks/SIEVE-T5/intervention_hypotheses.json`, `tasks/SIEVE-T5/recorded_run.json`, `tasks/SIEVE-T5/recorded_int01_run.json`, `tasks/SIEVE-T5/recorded_int02_run.json`, `tasks/SIEVE-T5/recorded_int03_run.json`.
- **Writes (creates or modifies):** `tests/fixtures/phase4/task-suite/SIEVE-T2-baseline-trace.json`, `tests/fixtures/phase4/task-suite/SIEVE-T4-baseline-trace.json`, `tests/fixtures/phase4/task-suite/SIEVE-T5-baseline-trace.json`, `tests/fixtures/phase4/task-suite/SIEVE-T5-held-out-edge-cases.json` — stable valid traces and the harness-only T5 oracle.
- **Writes (creates or modifies):** `tests/test_task_suite_phase4.py` — fixture isolation, recording validation, held-out-oracle, and recorded pipeline tests.

## Implementation notes

Each task must remain wholly under `tasks/<task_id>/{src,tests,task.md}`; the extra task-local recording files support deterministic execution and do not permit edits to Layer 1–3 code. The T5 held-out oracle is deliberately outside `tasks/SIEVE-T5/`, so `TaskRunner` may continue to copy the entire fixture unchanged without exposing the oracle to the agent workspace. `npm test` must pass after the recorded baseline solution executes in a copied workspace. Do not commit `node_modules`, lockfiles, generated Vitest caches, or run artifacts.

For every `intervention_constraints.json`, use the existing contract of non-empty `constraint_swaps` and matching non-empty `manual_reviews`. For every `intervention_hypotheses.json`, use `hypothesis_flips` and matching `manual_reviews` as specified by SIV-INT-007. Alternatives must be plausible and different from baseline values. The phase’s no-live-call CI rule means recordings, not live model calls, are the test oracle.

SIV-OPS-003 invokes every INT-01, INT-02, and INT-03 at `baseline.steps[0].step_id`. Therefore each new baseline must have at least one step, that first step must be `S001`, and every new INT-02/INT-03 alternative map must supply `S001`. The recorded INT-01/INT-02/INT-03 document must begin with that corresponding edited `S001` turn. Do not add a harness branch or a second target-selection convention.

`tests/fixtures/phase4/task-suite/SIEVE-T5-held-out-edge-cases.json` must include concrete unexposed cases such as empty input, repeated separators, whitespace-only tags, and duplicate tags. The fixture test must prove the agent-authored recorded test change covers the held-out list without exposing that list in `task.md` or the copied workspace; assert that `run_dir / "workspace" / "held_out_edge_cases.json"` does not exist after `TaskRunner.run("SIEVE-T5", ...)`.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_t2_t4_t5_recorded_documents_validate_as_agent_turn_sequences`; `test_t2_t4_t5_intervention_files_have_matching_nonempty_reviewed_s001_keys`; `test_t5_held_out_edge_case_oracle_has_unique_case_ids`. |
| Integration | `test_existing_task_runner_loads_each_new_fixture_without_harness_changes` runs each `task.md` and recorded backend through Layer 1; `test_existing_intervention_loader_accepts_each_constraint_fixture` verifies Layer 2 handoff. |
| System | `test_recorded_t2_t4_t5_baseline_plus_int01_produces_score_records` executes each complete recorded pipeline with `RecordedBackend`, the real `TaskRunner` subprocess invocation of each copied workspace's `npm test`, `InterventionRunner`, and the existing score runner; do not monkeypatch or mock any pipeline layer or Vitest subprocess. |
| Acceptance | `test_new_fixture_directories_are_isolated_and_each_runs_unmodified_through_existing_pipeline` asserts adding all three tasks changed no `src/sieve/` file and each fixture runs without a harness-specific branch. |
| Smoke | `test_t2_recorded_baseline_runs_and_writes_valid_trace` is the fastest new-fixture liveness check. |
| Sanity | `test_t2_boundary_t4_public_api_and_t5_held_out_cases_are_distinct_and_nonempty` asserts the category-specific intent is represented, and `test_new_recorded_scores_are_not_all_identical` feeds known recorded scores into `assert_nondegenerate`. |
| Regression | `test_phase4_new_task_baseline_trace_fixtures_match_recorded_baseline_output` compares deterministic trace outputs to the three committed fixture JSON files without live calls. |
| End-to-end | `test_cli_run_and_intervene_t4_int02_writes_trace_and_score` drives the existing CLI against T4’s public-API constraint fixture. |
| API | N/A — task fixture authoring and recorded backends make no Codex/GPT-5.6 request; API wrapper testing remains mocked in the intervention and orchestration prompts. |
| UI | N/A — task fixtures produce no static report; report rendering begins in SIV-RPT-001. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v`. The System and Acceptance tests in `tests/test_task_suite_phase4.py` must run real `npm test` commands only in copied workspaces after the recorded baseline applies its fix; do not run `npm test` directly in a source task fixture, because each fixture intentionally begins with a failing or edge-case-incomplete task test.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new and modified files.
- [ ] No data contract in §5 was altered; additive-only fixture and golden changes are noted in Traceability.
- [ ] Golden/regression fixtures, if authored, are committed with the code they characterize.
