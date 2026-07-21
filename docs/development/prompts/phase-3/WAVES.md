# Phase 3 — Dependency-Safe Executor Waves

Run waves in order. After every wave, collect each executor’s report and run:

```powershell
python -m pytest -v
python -m ruff check .
python -m black --check .
python -m mypy --strict .
```

Stop for any failing check, `deviation_flag`, out-of-scope write, unresolved
dependency, or contract ambiguity. Route planning ambiguity to
`sieve_ideator`; do not begin a later wave.

## Wave 1 — Independent metric primitives

- `SIV-MET-001-ast-patch-divergence.md`
- `SIV-MET-002-outcome-stability.md`

| Requirement | Writes |
|---|---|
| SIV-MET-001 | `pyproject.toml`, `src/sieve/diffing.py`, `tests/test_diffing.py` |
| SIV-MET-002 | `src/sieve/outcomes.py`, `tests/test_outcomes.py` |

Mechanical pairwise comparison:

| Pair | Shared write paths |
|---|---|
| SIV-MET-001 × SIV-MET-002 | none |

The two write sets are disjoint and neither prompt depends on the other, so
two executors may run concurrently.

Fan-out invocation:

```text
Spawn one sieve_executor for every prompt in docs/development/prompts/phase-3/WAVES.md Wave 1:
- docs/development/prompts/phase-3/SIV-MET-001-ast-patch-divergence.md
- docs/development/prompts/phase-3/SIV-MET-002-outcome-stability.md
Each executor must read docs/development/prompts/phase-3/_PREAMBLE.md first, honor its
declared write set, and report requirement ID, files touched, commands run,
tests passed, and deviation_flag. Do not start Wave 2 yet.
```

## Wave 2 — Score orchestration and CLI

- `SIV-MET-003-score-computation-and-degeneracy.md`

| Requirement | Writes |
|---|---|
| SIV-MET-003 | `src/sieve/schemas.py`, `src/sieve/scoring.py`, `src/sieve/persistence.py`, `src/sieve/cli.py`, `tests/test_scoring.py`, `tests/test_cli.py` |

Mechanical pairwise comparison: this wave has one prompt, so it has zero
write-set pairs and no possible in-wave collision. It depends on both Wave 1
metric interfaces.

Fan-out invocation:

```text
Spawn one sieve_executor for docs/development/prompts/phase-3/SIV-MET-003-score-computation-and-degeneracy.md only after Wave 1 passes the integration checkpoint. The executor must read docs/development/prompts/phase-3/_PREAMBLE.md first and report requirement ID, files touched, commands run, tests passed, and deviation_flag.
```

## Wave 3 — Golden regression lock

- `SIV-OPS-002-golden-score-regression.md`

| Requirement | Writes |
|---|---|
| SIV-OPS-002 | `tests/fixtures/phase3/t1-int01/baseline-trace.json`, `tests/fixtures/phase3/t1-int01/baseline-workspace/src/normalizeName.ts`, `tests/fixtures/phase3/t1-int01/perturbed-trace.json`, `tests/fixtures/phase3/t1-int01/perturbed-workspace/src/normalizeName.ts`, `tests/fixtures/phase3/t1-int01/expected-score.json`, `tests/fixtures/phase3/t3-int02/baseline-trace.json`, `tests/fixtures/phase3/t3-int02/baseline-workspace/src/formatUsername.ts`, `tests/fixtures/phase3/t3-int02/perturbed-trace.json`, `tests/fixtures/phase3/t3-int02/perturbed-workspace/src/formatUsername.ts`, `tests/fixtures/phase3/t3-int02/expected-score.json`, `tests/test_score_regression.py` |

Mechanical pairwise comparison: this wave has one prompt, so it has zero
write-set pairs and no possible in-wave collision. It depends on the complete
Wave 2 production score path.

Fan-out invocation:

```text
Spawn one sieve_executor for docs/development/prompts/phase-3/SIV-OPS-002-golden-score-regression.md only after Wave 2 passes the integration checkpoint. The executor must read docs/development/prompts/phase-3/_PREAMBLE.md first and report requirement ID, files touched, commands run, tests passed, and deviation_flag.
```

## Phase-close evidence

After Wave 3, run the full checkpoint above. Then produce two real recorded
run pairs, invoke:

```powershell
sieve score <run_id_baseline_t1> <run_id_perturbed_t1_int01>
sieve score <run_id_baseline_t3> <run_id_perturbed_t3_int02>
```

Validate both written `runs/<perturbed_run_id>/score.json` files against
`ScoreRecord`. The T1 INT-01 score must be zero and stable; the T3 INT-02
score must be positive and unstable; the two `faithfulness_score` values
must pass `assert_nondegenerate`. The two golden fixture comparisons must
also pass in CI without a live API call. This is the exact evidence required
to close the Phase 3 Definition of Done.
