# Phase 1 — Traceability Matrix

| Requirement ID | Prompt file | Wave | Depends on | Test types covered | DoD clause advanced |
|---|---|---:|---|---|---|
| SIV-INT-001 | `SIV-INT-001-context-replay.md` | 1 | none | Unit: concrete; Integration: concrete; System: N/A — no complete pipeline; Acceptance: N/A — SIV-INT-003 owns phase gate; Smoke: concrete; Sanity: concrete; Regression: N/A — no resumed output exists; End-to-end: N/A — no CLI; API: N/A — no wrapper call; UI: N/A — no report | Supplies the fixed verbatim context required to resume from baseline step 2. |
| SIV-INT-004 | `SIV-INT-004-step-budget-guard.md` | 1 | none | Unit: concrete; Integration: N/A — not integrated until SIV-INT-002; System: N/A — no backend or trace; Acceptance: N/A — SIV-INT-003 owns phase gate; Smoke: concrete; Sanity: concrete; Regression: N/A — no trace output; End-to-end: N/A — no CLI; API: N/A — no request; UI: N/A — no report | Bounds continuation generation while replaying from step 2. |
| SIV-INT-002 | `SIV-INT-002-resume-from-step.md` | 2 | SIV-INT-001, SIV-INT-004 | Unit: concrete; Integration: concrete; System: concrete; Acceptance: N/A — SIV-INT-003 owns independent phase gate; Smoke: concrete; Sanity: concrete; Regression: concrete; End-to-end: concrete; API: concrete plus manual-live N/A; UI: N/A — no report | Executes fixed-context regeneration at a requested step and creates the artifact SIV-INT-003 compares. |
| SIV-INT-003 | `SIV-INT-003-no-op-fidelity.md` | 3 | SIV-INT-002 | Unit: concrete; Integration: concrete; System: concrete; Acceptance: concrete; Smoke: concrete; Sanity: concrete; Regression: concrete; End-to-end: concrete; API: N/A — recorded backend is intentional CI evidence; UI: N/A — no report | Proves that a no-op replay from step 2 reproduces the original final diff. |

Each Phase 1 requirement appears exactly once. Every prompt has all ten taxonomy rows populated by concrete tests or a specific N/A reason; no data-contract changes are planned.
