# Phase 1 — Dependency-Safe Executor Waves

Run waves in numerical order. Do not start a later wave until every executor in the prior wave reports no deviation and the integration checkpoint passes.

## Wave 1

Prompts:

- `SIV-INT-001-context-replay.md`
- `SIV-INT-004-step-budget-guard.md`

Declared write sets:

| Prompt | Writes |
|---|---|
| SIV-INT-001 | `src/sieve/replay.py`, `tests/test_replay.py` |
| SIV-INT-004 | `src/sieve/budget.py`, `tests/test_budget.py` |

Mechanical pairwise intersection: `{src/sieve/replay.py, tests/test_replay.py} ∩ {src/sieve/budget.py, tests/test_budget.py} = ∅`. The write sets are disjoint and neither prompt depends on the other, so two `sieve_executor` agents may run concurrently.

Executor fan-out invocation:

```text
Spawn one sieve_executor per prompt in docs/prompts/phase-1/WAVES.md wave 1:
- docs/prompts/phase-1/SIV-INT-001-context-replay.md
- docs/prompts/phase-1/SIV-INT-004-step-budget-guard.md
Each executor must read docs/prompts/phase-1/_PREAMBLE.md first and report requirement ID, files touched, test pass/fail, and deviation_flag.
```

## Wave 2

Prompt:

- `SIV-INT-002-resume-from-step.md`

Declared write set:

| Prompt | Writes |
|---|---|
| SIV-INT-002 | `src/sieve/agent.py`, `src/sieve/runner.py`, `src/sieve/resume.py`, `src/sieve/cli.py`, `tasks/SIEVE-T1/recorded_resume_run.json`, `tests/test_agent.py`, `tests/test_runner.py`, `tests/test_resume.py`, `tests/test_cli.py` |

Mechanical pairwise comparison: one prompt has no sibling, so there are zero write-set pairs and no possible in-wave intersection. This prompt depends on both Wave 1 prompts.

Executor fan-out invocation:

```text
Spawn one sieve_executor for docs/prompts/phase-1/SIV-INT-002-resume-from-step.md only after Wave 1 passes the integration checkpoint. The executor must read docs/prompts/phase-1/_PREAMBLE.md first and report requirement ID, files touched, test pass/fail, and deviation_flag.
```

## Wave 3

Prompt:

- `SIV-INT-003-no-op-fidelity.md`

Declared write set:

| Prompt | Writes |
|---|---|
| SIV-INT-003 | `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json`, `tests/test_no_op_fidelity.py` |

Mechanical pairwise comparison: one prompt has no sibling, so there are zero write-set pairs and no possible in-wave intersection. This prompt depends on SIV-INT-002 because it executes the production resume path.

Executor fan-out invocation:

```text
Spawn one sieve_executor for docs/prompts/phase-1/SIV-INT-003-no-op-fidelity.md only after Wave 2 passes the integration checkpoint. The executor must read docs/prompts/phase-1/_PREAMBLE.md first and report requirement ID, files touched, test pass/fail, and deviation_flag.
```

## Checkpoint after every wave

Run `python -m pytest -v && python -m ruff check . && python -m black --check . && python -m mypy --strict .`. Stop for any deviation flag, out-of-scope write, unresolved dependency, or contract ambiguity. Only the final checkpoint plus the exact SIV-INT-003 test can close the Phase 1 DoD.
