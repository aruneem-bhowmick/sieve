# SIV-INT-005 — INT-01 claim deletion

## Traceability
- Phase: 2 — Intervention Core (SIEVE-SPEC.md §13)
- Requirement: INT-01 (claim deletion) implementation
- Wave: 2
- Depends on: SIV-SCH-002, SIV-INT-001, SIV-INT-002, SIV-INT-004
- Unblocks: SIV-INT-006
- Advances DoD: implements the reusable INT-01 execution path and proves it with a SIEVE-T1 baseline/perturbed pair; SIV-INT-006 applies the same path to SIEVE-T3 when that fixture exists.

## Objective

Implement the first real Layer 2 intervention. Given a completed baseline trace and target step, blank only that step’s `claim`, resume from the altered target through the existing bounded replay mechanism, and persist a distinct `run_type="perturbed"` trace whose metadata proves exactly what changed. Add a recorded SIEVE-T1 INT-01 run so the causal trace pair is reproducible without a live model call.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read `TraceRecord.task_id`, `steps`, `tool_results`, `final_diff`, and `test_result`; write a new §5.2 trace with `run_type="perturbed"` and an `InterventionMetadata` whose `type="INT-01"`, `target_step_id` is the selected ID, `target_field="claim"`, `original_value` is the baseline claim, and `replacement_value=""`.
- SIV-SCH-002 supplies ordered tool-result pairs; all new perturbed traces must explicitly supply one result for every new trace step.
- SIV-INT-001 and SIV-INT-002 supply fixed prefix context, workspace checkpoints, resumable backends, and the `StepBudget` guard. Do not duplicate their implementations.
- The relevant §15 risk is incoherent resumption. Reject a missing target, a non-baseline source trace, a non-INT-01 target field, an incorrect first regenerated step, or exhausted step budget rather than manufacturing a trace.

## Interface specification

```python
# src/sieve/interventions.py
class ClaimDeletion:
    type: Literal["INT-01"] = "INT-01"
    target_field: Literal["claim"] = "claim"

    def edit(self, baseline_step: StructuredReasoningStep) -> StructuredReasoningStep:
        """Return baseline_step with only claim replaced by the empty string."""

    def metadata(self, baseline_step: StructuredReasoningStep) -> InterventionMetadata:
        """Return complete INT-01 metadata for the altered step."""

class InterventionRunner:
    def __init__(self, repo_root: Path, runs_dir: Path, max_resumed_steps: int = 20) -> None:
        """Configure perturbed-run persistence and the resumed-step budget."""
    def run(
        self,
        baseline: TraceRecord,
        baseline_run_dir: Path,
        target_step_id: str,
        intervention: ClaimDeletion,
        backend: InterventionCodingAgentBackend,
    ) -> tuple[Path, TraceRecord]:
        """Execute one edited target step and persist its perturbed trace."""

# src/sieve/agent.py
class InterventionCodingAgentBackend(ResumableCodingAgentBackend, Protocol):
    def intervention_turn(
        self,
        task_prompt: str,
        replay_context: list[ReplayContextItem],
        edited_step: StructuredReasoningStep,
        history: list[ToolResultRecord],
    ) -> AgentTurn | None:
        """Return the first turn whose emitted step exactly equals edited_step."""

class OpenAIResponsesBackend:
    def intervention_turn(self, task_prompt: str, replay_context: list[ReplayContextItem], edited_step: StructuredReasoningStep, history: list[ToolResultRecord]) -> AgentTurn | None:
        """Request the edited target step and exactly one matching local action."""

class RecordedBackend:
    def intervention_turn(self, task_prompt: str, replay_context: list[ReplayContextItem], edited_step: StructuredReasoningStep, history: list[ToolResultRecord]) -> AgentTurn | None:
        """Return and validate the deterministic edited target turn."""

# src/sieve/cli.py
# Add `sieve intervene` with required --baseline-run-dir, --step, and --type INT-01;
# optional --runs-dir (Path("runs")), --max-resumed-steps (20), --live, and --model ("gpt-5.6").
```

`InterventionRunner.run` restores the checkpoint immediately before the target step, replays only `1..k-1` as `ReplayContextItem`s, calls `intervention_turn` for the edited step, then calls `resume_turn` for the continuation. The first returned turn must have the exact edited step values and a matching action; this prevents a backend from silently restoring the original claim. The continuation receives fixed prefix context plus the serialized edited target step. The runner executes every returned action through `TaskRunner._execute_turn`, preserves raw results in order, computes `final_diff` against the pristine task fixture, and persists a new run directory without touching the baseline artifacts.

## Files to create or modify

- **Reads:** `src/sieve/replay.py` — build immutable pre-target replay context.
- **Reads:** `src/sieve/resume.py` — match checkpoint restoration, bounded looping, persistence, and final-diff behavior.
- **Reads:** `src/sieve/runner.py` — reuse workspace-safe action execution and unified-directory diff calculation.
- **Reads:** `src/sieve/schemas.py` — construct valid `InterventionMetadata`, `TraceRecord`, and ordered raw tool-result pairs.
- **Reads:** `tasks/SIEVE-T1/recorded_run.json` — build the recorded baseline for the claim-deletion pair.
- **Writes (creates or modifies):** `src/sieve/interventions.py` — create `ClaimDeletion` and `InterventionRunner`.
- **Writes (creates or modifies):** `src/sieve/agent.py` — add the intervention backend protocol and context-aware OpenAI/recorded implementations.
- **Writes (creates or modifies):** `src/sieve/cli.py` — add the exact `intervene` command and default recorded INT-01 backend selection.
- **Writes (creates or modifies):** `tasks/SIEVE-T1/recorded_int01_run.json` — deterministic S001-empty-claim then S002 continuation recording.
- **Writes (creates or modifies):** `tests/test_interventions.py` — unit, integration, system, acceptance, smoke, sanity, and regression tests for INT-01.
- **Writes (creates or modifies):** `tests/test_agent.py` — mocked intervention request shape and recorded first-turn validation tests.
- **Writes (creates or modifies):** `tests/test_cli.py` — end-to-end `sieve intervene` behavior for INT-01.
- **Writes (creates or modifies):** `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json` — frozen recorded INT-01 trace containing complete metadata and raw result pairs.

## Implementation notes

The binding mechanism is: “Blank the `claim` field at the target step; resume.” The blank is exactly `""`, not whitespace, `null`, omission, or a placeholder. All other target-step fields must equal the baseline step, including `step_id`, `constraint`, `hypothesis`, `planned_action`, `action_target`, and `success_criterion`.

For a target at the first step, restore `checkpoints/initial`; otherwise restore the directory named by the immediately preceding recorded step ID. A perturbed trace never reuses the baseline `run_id`, timestamp, workspace, or `final_diff`. It must be rejected if `baseline.run_type != "baseline"`, if the requested ID is absent, or if the recorded/live backend does not return the edited target as its first generated step. This requirement does not score divergence and does not add an INT-03 pathway.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_claim_deletion_blanks_only_claim`; `test_claim_deletion_metadata_records_original_and_empty_replacement`; `test_intervention_runner_rejects_unknown_target`; and `test_intervention_runner_rejects_nonbaseline_source_trace`. Assert all non-claim fields are byte-for-byte equal after `model_dump`. |
| Integration | `test_int01_runner_uses_phase1_prefix_context_and_checkpoint`; `test_int01_runner_persists_tool_result_pairs`; and `test_intervention_runner_writes_trace_through_canonical_persistence`. Spy only at public production boundaries and load the written JSON with `TraceRecord.model_validate_json`. |
| System | `test_recorded_int01_sieve_t1_runs_baseline_then_perturbed_trace`: use `TaskRunner`, `InterventionRunner`, the recorded baseline/INT-01 backends, and the actual SIEVE-T1 fixture test command; assert baseline and perturbed run directories differ, both traces complete, and the altered target action executes. |
| Acceptance | `test_phase2_int01_sieve_t1_produces_paired_trace_records_with_populated_metadata`: assert exactly one baseline and one INT-01 trace for SIEVE-T1, equal task IDs, distinct UUIDs, `run_type="perturbed"` for the latter, complete metadata, and ordered step/result pairs. SIEVE-T3 matrix completion is intentionally deferred to SIV-INT-006 because the fixture does not yet exist. |
| Smoke | `test_int01_smoke_recorded_sieve_t1`: run recorded claim deletion at `TSIEVE-T1-S001` with a two-step budget and assert a persisted perturbed `trace.json`. |
| Sanity | `test_int01_edited_trace_has_one_empty_claim_and_no_other_target_field_change`: assert only the requested target claim is empty, no other claim is changed, and every tool result still matches the corresponding action. |
| Regression | `test_recorded_int01_sieve_t1_matches_phase2_golden_trace`: normalize UUID and timestamp, then compare the persisted trace with `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json`; this runs with no live call. |
| End-to-end | `test_cli_intervene_int01_creates_perturbed_trace`: create a recorded baseline under `tmp_path / "baseline-runs"`, invoke `sieve intervene` with that baseline directory and `tmp_path / "perturbed-runs"`, target `TSIEVE-T1-S001`, and type `INT-01`; assert the printed trace path contains valid INT-01 metadata. |
| API | `test_openai_intervention_turn_sends_fixed_prefix_and_exact_edited_step`: mock `responses.create`, assert the edited S001 JSON is sent after the prefix and before tool history, assert `response_tools()` is used, and reject a mock response whose emitted step differs from `edited_step`. Live smoke is N/A — §8 excludes live calls from CI. |
| UI | N/A — Phase 2 writes trace JSON for later visual comparison; the static report and its UI checks are Phase 4 scope. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_interventions.py tests/test_agent.py tests/test_cli.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new or modified files.
- [ ] No §5 field was altered; every new INT-01 trace has populated metadata and paired raw local results.
- [ ] The SIEVE-T1 recorded INT-01 trace and golden fixture are committed with the implementation.
