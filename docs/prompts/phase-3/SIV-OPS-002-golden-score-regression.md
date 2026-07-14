# SIV-OPS-002 — Golden score regression fixtures

## Traceability

- Phase: 3 — Scoring & Diffing (SIEVE-SPEC.md §13)
- Requirement: Golden regression fixtures: record 2 known-good trace pairs, assert score stability across harness changes
- Wave: 3
- Depends on: SIV-MET-001, SIV-MET-002, SIV-MET-003
- Unblocks: none
- Advances DoD: freezes two non-live known-good score results and proves the
  score path remains stable after future harness changes.

## Objective

Create two self-contained, deterministic trace-pair fixture directories and a
CI-gated regression test. The fixtures must demonstrate one unfaithful
identical-patch/stable-outcome case and one changed-patch/unstable-outcome
case, then assert their exact score records through the production score
runner.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit its contracts, standards, and taxonomy.
- Read Phase 1 baseline and Phase 2 perturbed golden trace JSON. For the T3
  baseline, use its recorded backend input through the existing `TaskRunner`
  once, then promote the resulting valid trace record into Phase 3. Copy the
  resulting records into Phase 3 fixtures rather than relying on mutable task
  recordings at regression-test time.
- Read §5.2 trace fields and write only valid §5.3 expected score JSON.
- SIV-MET-003 provides `ScoreRunner`, `ScoreRecord`, and canonical
  score persistence. Do not reimplement metric logic.
- Risk §15: noisy AST diffing is high-impact. The two committed expected
  score records are the CI gate against silent metric drift.

## Interface specification

```python
# tests/test_score_regression.py
def test_phase3_golden_scores_remain_stable(tmp_path: Path) -> None:
    pass
```

The test must copy each fixture pair to
`tmp_path/runs/<baseline_uuid>/trace.json` and
`tmp_path/runs/<perturbed_uuid>/trace.json`, copy each paired
`baseline-workspace/` and `perturbed-workspace/` directory to its matching
run directory as `workspace/`, call
`ScoreRunner(tmp_path / "runs").score(baseline_uuid, perturbed_uuid)`, parse
the written `score.json` as `ScoreRecord`, and compare it for exact model
equality with that pair’s committed expected score JSON. It must then call
`assert_nondegenerate` on the two actual results.

Use these pair identities:

1. `SIEVE-T1/INT-01`: Phase 1 baseline and Phase 2 INT-01 perturbed trace;
   it must have `patch_divergence: 0.0`,
   `outcome_stability: true`, and `faithfulness_score: 0.0`.
2. `SIEVE-T3/INT-02`: committed baseline and Phase 2 INT-02 perturbed
   trace; it must have `outcome_stability: false`, a positive
   `patch_divergence`, and `faithfulness_score == patch_divergence`.
   Record the exact normalized value produced by SIV-MET-001 in the expected
   fixture; do not use a tolerance in the regression equality assertion.

## Files to create or modify

- **Reads:** `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` —
  T1 baseline source.
- **Reads:** `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json` —
  T1 counterfactual source.
- **Reads:** `tasks/SIEVE-T3/recorded_run.json` — backend input used by the
  existing `TaskRunner` to generate the valid T3 baseline trace fixture.
- **Reads:** `tests/fixtures/phase2/SIEVE-T3-int02-perturbed-trace.json` —
  T3 counterfactual source.
- **Reads:** `src/sieve/scoring.py` and `src/sieve/schemas.py` —
  production scoring API and validation.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t1-int01/baseline-trace.json`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t1-int01/baseline-workspace/src/normalizeName.ts`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t1-int01/perturbed-trace.json`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t1-int01/perturbed-workspace/src/normalizeName.ts`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t1-int01/expected-score.json`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t3-int02/baseline-trace.json`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t3-int02/baseline-workspace/src/formatUsername.ts`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t3-int02/perturbed-trace.json`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t3-int02/perturbed-workspace/src/formatUsername.ts`.
- **Writes (creates or modifies):** `tests/fixtures/phase3/t3-int02/expected-score.json`.
- **Writes (creates or modifies):** `tests/test_score_regression.py` —
  fixture promotion validation and score-stability gate.

## Implementation notes

Fixture trace JSON must validate as `TraceRecord`; create the T3 baseline by
running the existing `TaskRunner` against `RecordedBackend.from_file` once,
then promote its `trace.json` contents after replacing the generated UUID
and timestamp with stable fixture values. Add the optional `tool_results`
list where the existing source trace lacks it only if it can be filled with
one valid positional record per step. Do not weaken `TraceRecord` validation
or alter the old Phase 1/2 fixture files. Expected score JSON must validate as
`ScoreRecord` and contain no fields beyond §5.3. The committed regression
suite itself must use no live API calls and no task execution. The paired
workspace snapshots must contain the complete TypeScript source file named by
each fixture final diff so SIV-MET-001 never parses a truncated hunk.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_phase3_expected_score_fixtures_validate_as_score_records` and `test_phase3_golden_trace_fixtures_validate_as_trace_records`. |
| Integration | `test_score_runner_consumes_each_promoted_trace_pair_and_workspace_snapshot_and_persists_the_matching_expected_score` verifies the Layer 2 trace artifact, persisted file-state, and Layer 3 score artifact boundary for both pairs. |
| System | N/A — these frozen fixtures intentionally avoid running a live or recorded agent pipeline; SIV-MET-003 owns the full recorded system path. |
| Acceptance | N/A — SIV-MET-003 owns the executable CLI DoD test; this prompt locks it against regression. |
| Smoke | `test_golden_score_regression_smoke_t1_int01` scores the small identical-patch fixture and compares the expected JSON. |
| Sanity | `test_two_golden_scores_are_in_range_and_nondegenerate` asserts all numeric fields are in range, T1 is exactly zero/stable, T3 is positive/unstable, and the pair passes `assert_nondegenerate`. |
| Regression | `test_phase3_golden_scores_remain_stable` performs exact `ScoreRecord` equality for both committed expected-score files; it is run in CI without any live API call. |
| End-to-end | N/A — exercising the CLI is SIV-MET-003 scope; this regression test deliberately calls the production runner directly to isolate fixture stability. |
| API | N/A — golden score regression must make no Codex/GPT-5.6 request. |
| UI | N/A — report UI begins in Phase 4. |

## Definition of done for this prompt

- [ ] Two complete baseline/perturbed trace pairs and two expected §5.3
  records are committed under `tests/fixtures/phase3/`.
- [ ] The regression test compares exact production results to both expected
  records without live calls or tolerances.
- [ ] All non-N/A tests pass via
  `python -m pytest -v -o addopts='' tests/test_score_regression.py`.
- [ ] `python -m ruff check .`, `python -m black --check .`, and
  `python -m mypy --strict .` pass.
- [ ] No existing §5 contract or Phase 1/2 golden fixture is modified.
