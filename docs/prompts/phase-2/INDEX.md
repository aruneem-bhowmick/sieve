# Phase 2 — Intervention Core Prompt Index

## Objective and increment

**Objective:** Real interventions (INT-01, INT-02) produce perturbed traces.

**Increment:** First real pre/post trace pairs exist; a human can visually compare a baseline and perturbed trace.

**Depends on:** Phase 1.

**Definition of Done:** INT-01 and INT-02 run successfully on SIEVE-T1 and SIEVE-T3, producing paired trace records per §5.2 with populated `intervention` fields.

Required final evidence: four perturbed records, one for every task/intervention combination, each paired to its task baseline.

## Execution order

| Order | Prompt | Requirement | Wave | Depends on | One-line deliverable |
|---:|---|---|---:|---|---|
| 1 | `SIV-SCH-002-tool-result-pairing.md` | SIV-SCH-002 | 1 | SIV-INT-001, SIV-INT-002, SIV-INT-003, SIV-INT-004 | Additive raw-result pairs for every newly persisted trace. |
| 2 | `SIV-INT-005-claim-deletion.md` | SIV-INT-005 | 2 | SIV-SCH-002, SIV-INT-001, SIV-INT-002, SIV-INT-004 | INT-01 SIEVE-T1 perturbed execution, metadata, CLI, and golden pair. |
| 3 | `SIV-INT-006-constraint-swap.md` | SIV-INT-006 | 3 | SIV-SCH-002, SIV-INT-005, SIV-INT-001, SIV-INT-002, SIV-INT-004 | Task-authored INT-02 alternatives, SIEVE-T3 fixture, and remaining three DoD counterfactual pairs. |

Dependency edges: `SIV-SCH-002 → SIV-INT-005 → SIV-INT-006`. Phase 1 requirements are already implemented prerequisites, not Phase 2 executor jobs. Wave order is deliberately sequential because each later prompt consumes code and trace representation made by the preceding one.

Before each wave, read `_PREAMBLE.md`; after each wave, run `python -m pytest -v && python -m ruff check . && python -m black --check . && python -m mypy --strict .`. Do not start a later wave if any executor reports a deviation, an out-of-scope write, an unresolved SIEVE-T3 fixture ambiguity, or an ADR-required contract change.

Wave 3 additionally requires the root Node preflight `npm ci` followed by `npm --prefix tasks/SIEVE-T3 test`. A host certificate-validation failure is an environment blocker: repair the trusted certificate chain before retrying, without changing repository dependencies or disabling TLS verification.
