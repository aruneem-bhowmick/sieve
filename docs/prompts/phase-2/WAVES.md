# Phase 2 — Dependency-Safe Executor Waves

Run waves in numerical order. Do not start a later wave until every executor in the prior wave reports no deviation and the integration checkpoint passes.

## Wave 1

Prompt:

- `SIV-SCH-002-tool-result-pairing.md`

Declared write set:

| Prompt | Writes |
|---|---|
| SIV-SCH-002 | `src/sieve/schemas.py`, `src/sieve/agent.py`, `src/sieve/runner.py`, `src/sieve/resume.py`, `tests/test_schemas.py`, `tests/test_runner.py`, `tests/test_resume.py`, `tests/test_agent.py`, `tests/fixtures/phase2/SIEVE-T1-tool-result-pairs.json` |

Mechanical pairwise comparison: one prompt has zero siblings, therefore zero write-set pairs and no possible in-wave intersection.

Executor fan-out invocation:

```text
Spawn one sieve_executor for docs/prompts/phase-2/SIV-SCH-002-tool-result-pairing.md only. The executor must read docs/prompts/phase-2/_PREAMBLE.md first and report requirement ID, files touched, test pass/fail, and deviation_flag.
```

## Wave 2

Prompt:

- `SIV-INT-005-claim-deletion.md`

Declared write set:

| Prompt | Writes |
|---|---|
| SIV-INT-005 | `src/sieve/interventions.py`, `src/sieve/agent.py`, `src/sieve/cli.py`, `tasks/SIEVE-T1/recorded_int01_run.json`, `tests/test_interventions.py`, `tests/test_agent.py`, `tests/test_cli.py`, `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json` |

Mechanical pairwise comparison: one prompt has zero siblings, therefore zero write-set pairs and no possible in-wave intersection. This prompt is after Wave 1 because every new perturbed trace must use SIV-SCH-002’s raw result-pair representation.

Executor fan-out invocation:

```text
Spawn one sieve_executor for docs/prompts/phase-2/SIV-INT-005-claim-deletion.md only after Wave 1 passes the integration checkpoint. The executor must read docs/prompts/phase-2/_PREAMBLE.md first and report requirement ID, files touched, test pass/fail, and deviation_flag.
```

## Wave 3

Prompt:

- `SIV-INT-006-constraint-swap.md`

Declared write set:

| Prompt | Writes |
|---|---|
| SIV-INT-006 | `src/sieve/interventions.py`, `src/sieve/cli.py`, `src/sieve/runner.py`, `tasks/SIEVE-T1/intervention_constraints.json`, `tasks/SIEVE-T1/recorded_int02_run.json`, `tasks/SIEVE-T3/package.json`, `tasks/SIEVE-T3/task.md`, `tasks/SIEVE-T3/src/formatUsername.ts`, `tasks/SIEVE-T3/tests/formatUsername.test.ts`, `tasks/SIEVE-T3/intervention_constraints.json`, `tasks/SIEVE-T3/recorded_run.json`, `tasks/SIEVE-T3/recorded_int01_run.json`, `tasks/SIEVE-T3/recorded_int02_run.json`, `tests/test_interventions.py`, `tests/test_cli.py`, `tests/test_runner.py`, `tests/fixtures/phase2/SIEVE-T1-int02-perturbed-trace.json`, `tests/fixtures/phase2/SIEVE-T3-int01-perturbed-trace.json`, `tests/fixtures/phase2/SIEVE-T3-int02-perturbed-trace.json` |

Mechanical pairwise comparison: one prompt has zero siblings, therefore zero write-set pairs and no possible in-wave intersection. It depends on Wave 2 because it extends the generic intervention runner and `sieve intervene` command instead of creating competing implementations.

Required environment preflight, before an executor reports this wave complete:

```text
From the repository root, run npm ci using the committed package-lock.json. On a Node 22 Windows host that trusts the registry certificate through the Windows certificate store, but not Node's bundled store, first set $env:NODE_USE_SYSTEM_CA = '1' for the current PowerShell process; this keeps TLS verification enabled and makes no persistent npm configuration change.
Then run python -m sieve.cli run --task SIEVE-T3 --runs-dir .verification-runs/phase2/t3-baseline.
The pristine SIEVE-T3 fixture intentionally fails; its recorded baseline edits the isolated workspace before executing npm test.
If npm ci still reports registry or proxy certificate validation failure, stop and report that host trust-chain error. Do not disable TLS verification, change npm registry settings, or create a task-local dependency lockfile.
```

Executor fan-out invocation:

```text
Spawn one sieve_executor for docs/prompts/phase-2/SIV-INT-006-constraint-swap.md only after Wave 2 passes the integration checkpoint. The executor must read docs/prompts/phase-2/_PREAMBLE.md first and report requirement ID, files touched, test pass/fail, and deviation_flag.
```

## Pairwise write-set proof

| Wave | Prompt pairs | Pairwise write-set intersection | Result |
|---:|---|---|---|
| 1 | none | no pairs exist | Disjoint |
| 2 | none | no pairs exist | Disjoint |
| 3 | none | no pairs exist | Disjoint |

The widest wave has one executor. Cross-wave intersections are intentional dependencies: Wave 1 and Wave 2 both write `src/sieve/agent.py` and `tests/test_agent.py`; Wave 1 and Wave 3 both write `src/sieve/runner.py` and `tests/test_runner.py`; Wave 2 and Wave 3 both write `src/sieve/interventions.py`, `src/sieve/cli.py`, `tests/test_interventions.py`, and `tests/test_cli.py`. No such intersection occurs within a wave.

## Checkpoint after every wave

Run `python -m pytest -v && python -m ruff check . && python -m black --check . && python -m mypy --strict .`. Stop for any deviation flag, out-of-scope write, unresolved dependency, missing task-fixture decision, or contract ambiguity. Only the final checkpoint plus four recorded pairs — SIEVE-T1 INT-01/INT-02 and SIEVE-T3 INT-01/INT-02 — can close the Phase 2 DoD.
