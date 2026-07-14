# Phase 2 — Traceability Matrix

| Requirement ID | Prompt file | Wave | Depends on | Test types covered | DoD clause advanced |
|---|---|---:|---|---|---|
| SIV-SCH-002 | `SIV-SCH-002-tool-result-pairing.md` | 1 | SIV-INT-001, SIV-INT-002, SIV-INT-003, SIV-INT-004 | Unit; Integration; System; Acceptance N/A — real intervention acceptance belongs to SIV-INT-005/006; Smoke; Sanity; Regression; End-to-end; API; UI N/A — report is Phase 4 | Paired trace records contain the raw action outcome for each step. |
| SIV-INT-005 | `SIV-INT-005-claim-deletion.md` | 2 | SIV-SCH-002, SIV-INT-001, SIV-INT-002, SIV-INT-004 | Unit; Integration; System; Acceptance; Smoke; Sanity; Regression; End-to-end; API; UI N/A — report is Phase 4 | Implements INT-01 and proves the first SIEVE-T1 baseline/perturbed pair. |
| SIV-INT-006 | `SIV-INT-006-constraint-swap.md` | 3 | SIV-SCH-002, SIV-INT-005, SIV-INT-001, SIV-INT-002, SIV-INT-004 | Unit; Integration; System; Acceptance; Smoke; Sanity; Regression; End-to-end; API; UI N/A — report is Phase 4 | Completes INT-01 and INT-02 on both T1 and T3, so all four perturbed traces have populated paired evidence. |

Every Phase 2 requirement has exactly one prompt. Every prompt has all ten §10 rows: concrete cases are specified where applicable, and the only N/A rows state the phase-specific absence of a static report or delegation of the phase-level acceptance assertion.
