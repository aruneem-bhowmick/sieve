# Phase 1 — Resume & Replay: Executor Preamble

Read this file before implementing any Phase 1 prompt. This package plans work only; no executor may alter a §5 data contract or a §8 binding standard without the ADR required by §14.

## Phase source — verbatim from SIEVE-SPEC.md §13

**Objective:** Prove the resumption mechanic works before building interventions on top of it.

**Increment:** A run can be resumed from an arbitrary step with unmodified context and produce a coherent continuation.

**Depends on:** Phase 0.

**DoD:** Resuming a completed baseline trace from its own step 2 (no field edited — a no-op intervention) reproduces the original trace's final diff, proving replay fidelity.

## Locked data contracts — verbatim from SIEVE-SPEC.md §5

### 5.1 Structured reasoning step

```json
{
  "step_id": "string, format T<task_id>-S<NNN>, monotonically increasing per task",
  "claim": "string — the factual assertion driving this step",
  "constraint": "string — the requirement this step believes it is satisfying",
  "hypothesis": "string — the agent's current theory of the problem",
  "planned_action": "enum: read_file | edit_file | run_tests | run_command | search",
  "action_target": "string — file path, command, or search query",
  "success_criterion": "string — how the agent will judge this step worked"
}
```

Every step is paired with the raw tool-call result(s) that followed it (SIV-SCH-002).

### 5.2 Trace record

```json
{
  "task_id": "string",
  "run_id": "string, uuid",
  "run_type": "baseline | perturbed",
  "intervention": {
    "type": "INT-01 | INT-02 | INT-03 | null",
    "target_step_id": "string | null",
    "target_field": "claim | constraint | hypothesis | null",
    "original_value": "string | null",
    "replacement_value": "string | null"
  },
  "steps": ["array of §5.1 objects"],
  "final_diff": "unified diff string",
  "test_result": { "passed": ["test ids"], "failed": ["test ids"] },
  "timestamp": "ISO 8601"
}
```

### 5.3 Score record

```json
{
  "task_id": "string",
  "intervention_type": "INT-01 | INT-02 | INT-03",
  "patch_divergence": "float, 0.0-1.0",
  "outcome_stability": "boolean — true if test pass/fail set unchanged",
  "faithfulness_score": "float, 0.0-1.0"
}
```

Phase 1 reads §5.1 and §5.2 only. It must preserve every existing field and field meaning. §5.3 is quoted because it is a locked contract, but it is not read or written by this phase.

## Binding resumption mechanic — verbatim from SIEVE-SPEC.md §6

Resumption mechanics (binding for every intervention): steps `1..k-1` are replayed as fixed context verbatim; step `k`'s target field is edited; generation resumes at step `k` and proceeds until the agent signals task completion or a step budget is exhausted (SIV-INT-004 defines the budget).

For Phase 1, no field is edited. The target baseline step is retained verbatim and the output remains a valid `TraceRecord`; `run_type` stays `baseline` because this is a fidelity replay, not a perturbed intervention.

## Binding standards checklist — condensed from SIEVE-SPEC.md §8

- [ ] Use Python 3.11+ for orchestration and preserve TypeScript task fixtures.
- [ ] Use the direct Codex/GPT-5.6 API wrapper; do not add an eval framework.
- [ ] Preserve the Phase 0 persistence layout: JSON artifacts under `runs/<run_id>/`.
- [ ] Use `pytest` for Layers 1–3 and task-local Vitest or Jest only for task fixtures.
- [ ] Run `python -m ruff check .`, `python -m black --check .`, and `python -m mypy --strict .`.
- [ ] CI uses mocked and recorded/golden tests; live API smoke calls are manual and never CI-gated.
- [ ] Do not implement scoring, AST diffing, reporting, or real INT-01/02/03 edits in this phase.

## Full test taxonomy — verbatim from SIEVE-SPEC.md §10

| Type | Meaning for Sieve |
|---|---|
| **Unit** | Individual functions: schema validation, AST-diff normalization, resumption context assembly, score computation. |
| **Integration** | Layer-to-layer contracts: Runner→Intervention Engine trace handoff, Intervention Engine→Report score handoff. |
| **System** | Full pipeline on a single task: baseline + one intervention → score record, no mocking. |
| **Acceptance** | Full pipeline meets a phase's Definition of Done end-to-end (e.g. "5-task suite produces a valid HTML report"). |
| **Smoke** | Fastest possible "is the harness alive" check: one task, one intervention, harness exits 0 and produces a score record. |
| **Sanity** | Spot-check that scores are in-range and not degenerate (e.g. not every score is exactly 0.0 or 1.0 — a sign of a broken diff or a no-op intervention). |
| **Regression** | Fixed golden traces (recorded once, replayed without live API calls) whose known scores must not silently change when harness code changes. |
| **End-to-end** | CLI invocation (`sieve run --task SIEVE-T1 --intervention INT-01`) through to a written report file on disk. |
| **API** | Direct tests of the Codex/GPT-5.6 API wrapper: request formation, structured-schema enforcement, resumption call shape. Mocked in CI; a small live-call smoke suite runs manually, never in CI, to avoid nondeterministic gating. |
| **UI** | The static HTML report: does the 2×2 render correctly, does the per-task score table populate, is it non-blank. No traditional GUI exists otherwise, so this is scoped narrowly and correctly to the report artifact. |

## Execution order

1. Wave 1: `SIV-INT-001-context-replay.md` and `SIV-INT-004-step-budget-guard.md` may execute concurrently.
2. Wave 2: `SIV-INT-002-resume-from-step.md` executes after both Wave 1 prompts.
3. Wave 3: `SIV-INT-003-no-op-fidelity.md` executes after Wave 2.

Run the integration checkpoint after each wave: `python -m pytest -v && python -m ruff check . && python -m black --check . && python -m mypy --strict .`. Stop and return to the ideator for any contract conflict, dependency ambiguity, or out-of-scope write.
