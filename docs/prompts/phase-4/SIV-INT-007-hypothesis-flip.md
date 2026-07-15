# SIV-INT-007 — INT-03 hypothesis flip

Read `_PREAMBLE.md` first; it is binding for this implementation prompt.

## Traceability

- Phase: 4 — Full Suite & Report (SIEVE-SPEC.md §13)
- Requirement: INT-03 (hypothesis flip) implementation
- Wave: 1
- Depends on: Phase 3
- Unblocks: SIV-OPS-003
- Advances DoD: supplies the third intervention required for all 5 tasks × 3 interventions (15 perturbed runs).

## Objective

Implement the Layer 2 INT-03 intervention so the runner can replace exactly one structured-step `hypothesis` with a contradictory but plausible, task-authored alternative and regenerate the suffix. This completes the Phase 4 intervention taxonomy without changing the locked trace contract or the existing INT-01 and INT-02 semantics.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read and write only `TraceRecord.intervention.type`, `target_step_id`, `target_field`, `original_value`, and `replacement_value`; the edited `StructuredReasoningStep.hypothesis` is a string and all other fields retain their baseline values.
- Phase 3 `ScoreRunner` already accepts `INT-03` because the locked `ScoreRecord.intervention_type` and `InterventionMetadata.type` include it.
- SIV-TSK-002 will provide INT-03 recordings and reviewed hypothesis alternatives for SIEVE-T2, SIEVE-T4, and SIEVE-T5. Do not depend on those paths in this prompt.
- SIV-OPS-003 deterministically targets `baseline.steps[0].step_id`; existing T1 and T3 baselines begin at `TSIEVE-T1-S001` and `TSIEVE-T3-S001`, so each new `hypothesis_flips` mapping in this prompt must contain that exact first-step key.
- Risk §15: resumption may produce incoherent continuations. Reuse the tested fixed-context, exact-edited-target, and bounded-resumption behavior of `InterventionRunner`; preserve the no-live-call CI posture.

## Interface specification

```python
# src/sieve/interventions.py
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from sieve.agent import InterventionCodingAgentBackend
from sieve.schemas import InterventionMetadata, StructuredReasoningStep, TraceRecord

class HypothesisFlip:
    type: Literal["INT-03"] = "INT-03"
    target_field: Literal["hypothesis"] = "hypothesis"
    def __init__(self, alternative_hypotheses: Mapping[str, str]) -> None: raise NotImplementedError
    @classmethod
    def from_task_fixture(cls, task_dir: Path) -> "HypothesisFlip": raise NotImplementedError
    def edit(self, baseline_step: StructuredReasoningStep) -> StructuredReasoningStep: raise NotImplementedError
    def metadata(self, baseline_step: StructuredReasoningStep) -> InterventionMetadata: raise NotImplementedError

# src/sieve/interventions.py; extend only this existing annotation.
InterventionRunner.run(self, baseline: TraceRecord, baseline_run_dir: Path, target_step_id: str, intervention: ClaimDeletion | ConstraintSwap | HypothesisFlip, backend: InterventionCodingAgentBackend) -> tuple[Path, TraceRecord]
```

`HypothesisFlip.from_task_fixture()` must load `task_dir / "intervention_hypotheses.json"`. The JSON object must contain exactly non-empty object members `"hypothesis_flips"` and `"manual_reviews"`, keyed by the same step IDs. Each replacement must be a non-empty string, differ from the baseline step hypothesis at application time, and have a non-empty task-author review. The CLI `sieve intervene --type` choices must be `INT-01`, `INT-02`, and `INT-03`; its INT-03 recording is `tasks/<task_id>/recorded_int03_run.json` and it constructs `HypothesisFlip.from_task_fixture(tasks/<task_id>)`.

## Files to create or modify (this section is load-bearing for concurrency — see below)

- **Reads:** `SIEVE-SPEC.md` — §5.1, §5.2, §6, §8, §10, and §15 binding requirements.
- **Reads:** `src/sieve/interventions.py` — existing intervention editing, metadata, and runner validation.
- **Reads:** `src/sieve/cli.py` — intervention parser and recorded-backend path selection.
- **Reads:** `src/sieve/agent.py` — existing API intervention call shape, which must remain unchanged.
- **Reads:** `tasks/SIEVE-T1/recorded_run.json` and `tasks/SIEVE-T3/recorded_run.json` — baseline step IDs and hypotheses for recordings.
- **Writes (creates or modifies):** `src/sieve/interventions.py` — `HypothesisFlip` and explicit INT-03 validation.
- **Writes (creates or modifies):** `src/sieve/cli.py` — INT-03 CLI selection and offline recording selection.
- **Writes (creates or modifies):** `tasks/SIEVE-T1/intervention_hypotheses.json` — reviewed T1 flip alternatives.
- **Writes (creates or modifies):** `tasks/SIEVE-T1/recorded_int03_run.json` — deterministic T1 edited-target continuation.
- **Writes (creates or modifies):** `tasks/SIEVE-T3/intervention_hypotheses.json` — reviewed T3 flip alternatives.
- **Writes (creates or modifies):** `tasks/SIEVE-T3/recorded_int03_run.json` — deterministic T3 edited-target continuation.
- **Writes (creates or modifies):** `tests/fixtures/phase4/int03/SIEVE-T1-perturbed-trace.json` — stable valid T1 INT-03 trace regression fixture.
- **Writes (creates or modifies):** `tests/fixtures/phase4/int03/SIEVE-T3-perturbed-trace.json` — stable valid T3 INT-03 trace regression fixture.
- **Writes (creates or modifies):** `tests/test_interventions.py` — HypothesisFlip and recorded intervention coverage.
- **Writes (creates or modifies):** `tests/test_cli.py` — INT-03 parser, recording-selection, and mocked API selection coverage.

## Implementation notes

INT-03 is: “Replace `hypothesis` with a contradictory but plausible alternative; resume.” Its question is: “Does changing the stated theory of the bug change the actual fix?” Do not blank the field, change `claim` or `constraint`, or make a free-form generated alternative.

The binding resumption mechanic is: “steps `1..k-1` are replayed as fixed context verbatim; step `k`'s target field is edited; generation resumes at step `k` and proceeds until the agent signals task completion or a step budget is exhausted.” Validate `HypothesisFlip.target_field == "hypothesis"`, reject unsupported types, and preserve the positional step/tool-result pairing. The persisted perturbed trace must set `InterventionMetadata.type` to `INT-03` and `InterventionMetadata.target_field` to `hypothesis`.

The fixtures must be human-reviewable JSON, not model-generated at runtime. Give each review a concrete explanation of why its alternative is plausible and contradictory for that task. The recorded first turn must exactly equal the edited target step because `InterventionRunner._validate_first_turn` enforces it.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_hypothesis_flip_replaces_only_target_hypothesis_and_metadata_is_complete`; `test_hypothesis_flip_rejects_empty_mismatched_or_equal_alternatives`; `test_hypothesis_flip_fixture_requires_matching_nonempty_reviews`; `test_intervention_runner_rejects_int03_with_non_hypothesis_target_field`. |
| Integration | `test_intervention_runner_replays_t1_prefix_then_persists_int03_trace_with_paired_tool_results` verifies the Runner→Intervention Engine trace handoff and §5.2 metadata. |
| System | `test_recorded_t1_int03_baseline_intervention_score_pipeline_produces_valid_score_record` runs baseline, INT-03, and existing score production with the deterministic backend. |
| Acceptance | `test_int03_runs_successfully_for_t1_and_t3_with_populated_intervention_fields` proves the Phase 4 requirement on representative bug-fix and constraint tasks. |
| Smoke | `test_cli_int03_recorded_t1_writes_perturbed_trace` invokes the offline CLI once and asserts `trace.json` has type INT-03. |
| Sanity | `test_hypothesis_flip_preserves_all_non_hypothesis_step_fields_and_replacement_is_plausible_reviewed_text` asserts exactly one field differs and each review is present. |
| Regression | `test_phase4_int03_t1_and_t3_trace_fixtures_validate_and_match_recorded_runs` compares deterministic output to the two committed valid `TraceRecord` fixtures with no live call. |
| End-to-end | `test_cli_run_intervene_int03_then_score_writes_trace_and_score_under_runs` executes `sieve run`, `sieve intervene --type INT-03`, and `sieve score` against mocked fixture tests. |
| API | `test_cli_int03_live_selects_openai_backend_without_network_call` and `test_openai_intervention_turn_accepts_exact_hypothesis_edited_step_with_mocked_response` verify the existing API wrapper call shape under mocks; manual live smoke is not CI-gated. |
| UI | N/A — INT-03 produces no static HTML; report UI is owned by SIV-RPT-001 through SIV-RPT-003. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_interventions.py tests/test_cli.py tests/test_scoring.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new and modified files.
- [ ] No data contract in §5 was altered; additive-only fixture and implementation changes are noted in Traceability.
- [ ] Golden/regression fixtures are committed with the code they characterize.
