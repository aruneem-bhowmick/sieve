# Phase 4 Executor Waves

Read `_PREAMBLE.md` and the named prompt before starting each worker. Run the
mandatory project gate and review every executor deviation flag between
waves: `python -m pytest -v && python -m ruff check . && python -m black
--check . && python -m mypy --strict .`.

## Wave 1 — three independent prompts

Prompts:

- `SIV-INT-007` writes `src/sieve/interventions.py`, `src/sieve/cli.py`, `tests/test_interventions.py`, `tests/test_cli.py`, `tasks/SIEVE-T1/recorded_int03_run.json`, `tasks/SIEVE-T3/recorded_int03_run.json`, and `tests/fixtures/phase4/int03/`.
- `SIV-TSK-002` writes only `tasks/SIEVE-T2/`, `tasks/SIEVE-T4/`, `tasks/SIEVE-T5/`, `tests/test_task_suite_phase4.py`, and `tests/fixtures/phase4/task-suite/`.
- `SIV-RPT-001` writes `src/sieve/reporting.py`, `tests/test_reporting.py`, and `tests/fixtures/phase4/reporting/`.

Mechanical pairwise write-set comparison:

| Pair | Shared exact write path | Result |
|---|---|---|
| SIV-INT-007 × SIV-TSK-002 | none | disjoint |
| SIV-INT-007 × SIV-RPT-001 | none | disjoint |
| SIV-TSK-002 × SIV-RPT-001 | none | disjoint |

Fan out exactly as follows:

```text
Spawn one sieve_executor per prompt in docs/prompts/phase-4/WAVES.md wave 1:
- SIV-INT-007 — docs/prompts/phase-4/SIV-INT-007-hypothesis-flip.md
- SIV-TSK-002 — docs/prompts/phase-4/SIV-TSK-002-add-t2-t4-t5-fixtures.md
- SIV-RPT-001 — docs/prompts/phase-4/SIV-RPT-001-html-report-generator.md
Wait for all of them, then summarize each: requirement ID, files touched, test pass/fail, and any reported deviation or out-of-scope-write flag.
```

## Wave 2 — headline visual

Prompt: `SIV-RPT-002`.

It depends on SIV-RPT-001 and deliberately writes the same reporting module,
report tests, and report fixtures. It also owns root `package.json`,
`package-lock.json`, and `tools/render_report_screenshot.mjs` for the
manual-reviewed screenshot renderer. It must not be run concurrently with
any other Phase 4 prompt.

```text
Spawn one sieve_executor for docs/prompts/phase-4/SIV-RPT-002-headline-two-by-two-grid.md. Read _PREAMBLE.md first. Report requirement ID, files touched, test pass/fail, and any deviation flag.
```

After the executor reports clean, the integrator—not the executor—must run the full mandatory project gate stated above and inspect `git diff --check` before accepting this wave.

## Wave 3 — limitations content

Prompt: `SIV-RPT-003`.

It depends on SIV-RPT-001 and SIV-RPT-002 and deliberately writes the same
reporting module and report tests; this single-prompt wave is vacuously
write-disjoint.

```text
Spawn one sieve_executor for docs/prompts/phase-4/SIV-RPT-003-honest-limitations.md. Read _PREAMBLE.md first. Report requirement ID, files touched, test pass/fail, and any deviation flag.
```

## Wave 4 — full-suite orchestration

Prompt: `SIV-OPS-003`.

It depends on all prior Phase 4 requirements and writes shared CLI/test
surfaces after their owners are complete; this single-prompt wave is
vacuously write-disjoint.

```text
Spawn one sieve_executor for docs/prompts/phase-4/SIV-OPS-003-run-suite-command.md. Read _PREAMBLE.md first. Report requirement ID, files touched, test pass/fail, and any deviation flag.
```
