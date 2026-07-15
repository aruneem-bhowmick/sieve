# Phase 4 Traceability Matrix

| Requirement ID | Prompt file | Wave | Depends on | Test types covered | DoD clause advanced |
|---|---|---:|---|---|---|
| SIV-INT-007 | `SIV-INT-007-hypothesis-flip.md` | 1 | Phase 3 | Unit, Integration, System, Acceptance, Smoke, Sanity, Regression, End-to-end, API, UI (N/A — no report artifact) | All 5 tasks × 3 interventions complete. |
| SIV-TSK-002 | `SIV-TSK-002-add-t2-t4-t5-fixtures.md` | 1 | Phase 3 | Unit, Integration, System, Acceptance, Smoke, Sanity, Regression, End-to-end, API (N/A — fixture work makes no API request), UI (N/A — no report artifact) | All 5 tasks can participate in 15 perturbed runs and 5 baselines. |
| SIV-RPT-001 | `SIV-RPT-001-html-report-generator.md` | 1 | Phase 3 | Unit, Integration, System, Acceptance, Smoke, Sanity, Regression, End-to-end, API (N/A — report generation makes no API request), UI | `report.html` renders correctly and contains the per-task/per-intervention data. |
| SIV-RPT-002 | `SIV-RPT-002-headline-two-by-two-grid.md` | 2 | SIV-RPT-001 | Unit, Integration, System, Acceptance, Smoke, Sanity, Regression, End-to-end, API (N/A — grid rendering makes no API request), UI | `report.html` renders the 2×2 headline visual. |
| SIV-RPT-003 | `SIV-RPT-003-honest-limitations.md` | 3 | SIV-RPT-001, SIV-RPT-002 | Unit, Integration, System, Acceptance, Smoke, Sanity, Regression, End-to-end, API (N/A — static content makes no API request), UI | Honest Limitations section is present in the rendered report. |
| SIV-OPS-003 | `SIV-OPS-003-run-suite-command.md` | 4 | SIV-INT-007, SIV-TSK-002, SIV-RPT-001, SIV-RPT-002, SIV-RPT-003 | Unit, Integration, System, Acceptance, Smoke, Sanity, Regression, End-to-end, API, UI | Entire Phase 4 DoD, including real-data demo support, is produced by one command. |
