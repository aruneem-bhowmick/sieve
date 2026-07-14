# Phase 3 — Traceability Matrix

| Requirement ID | Prompt file | Wave | Depends on | Test types covered | DoD clause advanced |
|---|---|---:|---|---|---|
| SIV-MET-001 | `SIV-MET-001-ast-patch-divergence.md` | 1 | Phase 2 | Unit; Integration N/A — no handoff until SIV-MET-003; System N/A — pipeline owned by SIV-MET-003; Acceptance N/A — CLI DoD owned by SIV-MET-003; Smoke; Sanity; Regression N/A — SIV-OPS-002 owns goldens; End-to-end N/A — no CLI; API N/A — no API request; UI N/A — Phase 4 report | Structural normalized patch-divergence field. |
| SIV-MET-002 | `SIV-MET-002-outcome-stability.md` | 1 | Phase 2 | Unit; Integration; System N/A — pipeline owned by SIV-MET-003; Acceptance N/A — CLI DoD owned by SIV-MET-003; Smoke; Sanity; Regression N/A — SIV-OPS-002 owns goldens; End-to-end N/A — no CLI; API N/A — no API request; UI N/A — Phase 4 report | Boolean test-outcome-stability field. |
| SIV-MET-003 | `SIV-MET-003-score-computation-and-degeneracy.md` | 2 | SIV-MET-001, SIV-MET-002 | Unit; Integration; System; Acceptance; Smoke; Sanity; Regression N/A — SIV-OPS-002 owns frozen scores; End-to-end; API N/A — local-only scoring; UI N/A — Phase 4 report | Required score CLI, valid §5.3 persistence, and executable non-degeneracy check. |
| SIV-OPS-002 | `SIV-OPS-002-golden-score-regression.md` | 3 | SIV-MET-001, SIV-MET-002, SIV-MET-003 | Unit; Integration; System N/A — intentionally frozen artifacts; Acceptance N/A — SIV-MET-003 owns CLI DoD; Smoke; Sanity; Regression; End-to-end N/A — direct runner isolates regression; API N/A — no API calls; UI N/A — Phase 4 report | Two CI-gated known-good score pairs retain stable results. |

Every Phase 3 requirement has exactly one prompt. Every prompt contains all
ten §10 rows with concrete tests or a specific scope reason for N/A.
