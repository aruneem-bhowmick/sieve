# Phase 3 — Scoring & Diffing Prompt Index

**Objective:** Turn trace pairs into numbers.

**Increment:** A faithfulness score exists for real (task, intervention) pairs.

**Depends on:** Phase 2.

**Definition of Done:** `sieve score <run_id_baseline> <run_id_perturbed>`
produces a valid §5.3 score record; scores are sane (not degenerate —
SIV-MET-003).

Phase 2 is verified complete: all four required INT-01/INT-02 × SIEVE-T1/T3
paired trace records exist with populated metadata, the dedicated DoD test
passes, and the full project gate passed before this package was created.

| Execution order | Prompt | Requirement | Wave | Depends on | One-line outcome |
|---:|---|---|---:|---|---|
| 1 | [SIV-MET-001-ast-patch-divergence.md](SIV-MET-001-ast-patch-divergence.md) | SIV-MET-001 | 1 | Phase 2 | Tree-sitter structural patch distance in `[0.0, 1.0]`. |
| 2 | [SIV-MET-002-outcome-stability.md](SIV-MET-002-outcome-stability.md) | SIV-MET-002 | 1 | Phase 2 | Exact pass/fail-set stability comparison. |
| 3 | [SIV-MET-003-score-computation-and-degeneracy.md](SIV-MET-003-score-computation-and-degeneracy.md) | SIV-MET-003 | 2 | SIV-MET-001, SIV-MET-002 | Score model, runner, non-degeneracy guard, persistence, and CLI. |
| 4 | [SIV-OPS-002-golden-score-regression.md](SIV-OPS-002-golden-score-regression.md) | SIV-OPS-002 | 3 | SIV-MET-001, SIV-MET-002, SIV-MET-003 | Two frozen trace pairs with exact CI score regression evidence. |

Dependency graph:

```text
SIV-MET-001 ─┐
             ├── SIV-MET-003 ─── SIV-OPS-002
SIV-MET-002 ─┘
```

The Wave 1 prompts share no writes. Wave 2 is deliberately singular because
the score runner integrates both metrics and owns the shared CLI, schema, and
persistence changes. Wave 3 is singular because it freezes the completed
production scoring behavior.
