# Phase 1 — Resume & Replay: Prompt Index

## Scope

- **Objective:** Prove the resumption mechanic works before building interventions on top of it.
- **Increment:** A run can be resumed from an arbitrary step with unmodified context and produce a coherent continuation.
- **Depends on:** Phase 0.
- **Definition of Done:** Resuming a completed baseline trace from its own step 2 (no field edited — a no-op intervention) reproduces the original trace's final diff, proving replay fidelity.

Phase 0 was verified before this plan: `sieve run --task SIEVE-T1` produced a validated trace under `.verification-runs/phase0/`; `pytest -v`, `ruff check .`, `black --check .`, and `mypy --strict .` passed locally; and the repository’s GitHub Actions CI history reports successful runs on `main`.

## Execution order

| Order | Wave | Prompt | Requirement | Description | Depends on |
|---:|---:|---|---|---|---|
| 1 | 1 | [SIV-INT-001-context-replay.md](SIV-INT-001-context-replay.md) | SIV-INT-001 | Build immutable, verbatim prior-step API context. | none |
| 2 | 1 | [SIV-INT-004-step-budget-guard.md](SIV-INT-004-step-budget-guard.md) | SIV-INT-004 | Build an independent bound for newly generated resume steps. | none |
| 3 | 2 | [SIV-INT-002-resume-from-step.md](SIV-INT-002-resume-from-step.md) | SIV-INT-002 | Implement recorded/live resume execution and the `sieve resume` command. | SIV-INT-001, SIV-INT-004 |
| 4 | 3 | [SIV-INT-003-no-op-fidelity.md](SIV-INT-003-no-op-fidelity.md) | SIV-INT-003 | Add the exact final-diff acceptance and golden regression gate. | SIV-INT-002 |

## Dependency edges

```text
SIV-INT-001 ─┐
             ├── SIV-INT-002 ─── SIV-INT-003
SIV-INT-004 ─┘
```

No dependency is inferred solely from shared source reads. Every cross-prompt write is sequenced either by the explicit functional dependency above or by a separate wave.

## Executor handoff

Each executor must read `_PREAMBLE.md`, then only its assigned prompt. Run one wave at a time. After every wave, the integrator runs `python -m pytest -v && python -m ruff check . && python -m black --check . && python -m mypy --strict .`, reviews executor deviation flags, and stops on any out-of-scope write or data-contract ambiguity.
