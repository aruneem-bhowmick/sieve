# Phase 4 — Full Suite & Report

**Objective:** Complete Build Week deliverable — full task suite, all three interventions, rendered report.

**Increment:** The judge-facing artifact: `report.html` with the 2×2 and per-task table.

**Depends on:** Phase 3.

**Definition of Done:** All 5 tasks × 3 interventions (15 perturbed runs + 5 baselines) complete, `report.html` renders correctly, demo narrative (§11) is fully supported by real data, Honest Limitations section is present in the rendered report.

Read [_PREAMBLE.md](_PREAMBLE.md) before executing any prompt.

| Order | Prompt | Requirement | Wave | Depends on | Description |
|---:|---|---|---:|---|---|
| 1 | [SIV-INT-007-hypothesis-flip.md](SIV-INT-007-hypothesis-flip.md) | SIV-INT-007 | 1 | Phase 3 | Adds the third one-field intervention and its offline recorded path. |
| 2 | [SIV-TSK-002-add-t2-t4-t5-fixtures.md](SIV-TSK-002-add-t2-t4-t5-fixtures.md) | SIV-TSK-002 | 1 | Phase 3 | Adds isolated TypeScript fixtures for T2, T4, and T5 with deterministic recordings. |
| 3 | [SIV-RPT-001-html-report-generator.md](SIV-RPT-001-html-report-generator.md) | SIV-RPT-001 | 1 | Phase 3 | Reads persisted scores plus sibling perturbed traces and creates the static table/report shell. |
| 4 | [SIV-RPT-002-headline-two-by-two-grid.md](SIV-RPT-002-headline-two-by-two-grid.md) | SIV-RPT-002 | 2 | SIV-RPT-001 | Adds the §7.3 pass/broke 2×2 headline grid and reproducible manual screenshot regression. |
| 5 | [SIV-RPT-003-honest-limitations.md](SIV-RPT-003-honest-limitations.md) | SIV-RPT-003 | 3 | SIV-RPT-001, SIV-RPT-002 | Embeds all three required limitations in every generated report. |
| 6 | [SIV-OPS-003-run-suite-command.md](SIV-OPS-003-run-suite-command.md) | SIV-OPS-003 | 4 | SIV-INT-007, SIV-TSK-002, SIV-RPT-001, SIV-RPT-002, SIV-RPT-003 | Runs the 5×3 matrix, writes scores, and emits the finished report in one command. |

The only concurrent wave is Wave 1. Its prompts have pairwise-disjoint write
sets; later waves intentionally serialize edits to the report generator.
