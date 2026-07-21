# SIV-INT-002 — Resume-from-step

## Traceability
- Phase: 1 — Resume & Replay (SIEVE-SPEC.md §13)
- Requirement: Resume-from-step: regenerate from step `k` forward given replayed context
- Wave: 2
- Depends on: SIV-INT-001, SIV-INT-004
- Unblocks: SIV-INT-003
- Advances DoD: implements the replay execution path that must regenerate the baseline final diff from step 2.

## Objective

Implement the Layer 2 resumption runner and `sieve resume` command. It must take a completed baseline trace plus its run directory, reconstruct fixed context before a target step through SIV-INT-001, restore the recorded workspace checkpoint immediately before that step, regenerate from the target step forward through a backend, enforce SIV-INT-004’s new-step budget, and persist a valid replay result without editing any reasoning field.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read `TraceRecord.task_id`, `run_id`, `steps`, `final_diff`, `test_result`, and `timestamp`; build a new valid §5.2 `TraceRecord` with the same task ID, `run_type="baseline"`, and empty `InterventionMetadata`. The resumed trace’s `run_id` and `timestamp` are new values. Read the additive filesystem checkpoint named by the immediately prior `StructuredReasoningStep.step_id` beneath `baseline_run_dir/checkpoints/`, rather than adding a field to §5.2.
- SIV-INT-001 provides `build_replay_context`; SIV-INT-004 provides `StepBudget` and `StepBudgetExceeded`.
- Risk: “Resumption produces incoherent continuations.” Fail on an absent target step, an exhausted budget, or a generated step ID that is not strictly after the fixed replay context; do not silently repair generated reasoning.

## Interface specification

```python
# src/sieve/agent.py
class ResumableCodingAgentBackend(CodingAgentBackend, Protocol):
    def resume_turn(
        self,
        task_prompt: str,
        replay_context: list[ReplayContextItem],
        history: list[ToolResult],
    ) -> AgentTurn | None:
        """Return the next regenerated turn, or completion."""

class OpenAIResponsesBackend:
    def resume_turn(
        self,
        task_prompt: str,
        replay_context: list[ReplayContextItem],
        history: list[ToolResult],
    ) -> AgentTurn | None:
        """Make a schema-constrained API resumption request."""

class RecordedBackend:
    def resume_turn(
        self,
        task_prompt: str,
        replay_context: list[ReplayContextItem],
        history: list[ToolResult],
    ) -> AgentTurn | None:
        """Return a deterministic recorded resumption turn."""

    @classmethod
    def from_file_from_step(
        cls, path: Path, target_step_id: str
    ) -> "RecordedBackend":
        """Load only recorded turns whose step sequence begins at target_step_id."""

# src/sieve/resume.py
class ResumeRunner:
    def __init__(self, repo_root: Path, runs_dir: Path, max_resumed_steps: int = 20) -> None:
        """Configure a fresh-workspace replay runner."""
    def resume(
        self,
        baseline: TraceRecord,
        baseline_run_dir: Path,
        target_step_id: str,
        backend: ResumableCodingAgentBackend,
    ) -> tuple[Path, TraceRecord]:
        """Regenerate and persist a no-op replay from target_step_id."""

# src/sieve/cli.py
# The `resume` parser requires these arguments:
# --baseline-run-dir Path
# --step str
# --runs-dir Path, defaulting to Path("runs")
# --max-resumed-steps int, defaulting to 20
# --live and --model, with model defaulting to "gpt-5.6"
```

`TaskRunner.run` must create an additive `checkpoints/` directory under its run directory. After successfully executing each baseline turn, it must copy the workspace to a child directory named with that turn’s exact `step_id`; before the first step it must copy the untouched fixture to `checkpoints/initial/`. These paths are filesystem evidence, not §5 JSON fields. `OpenAIResponsesBackend.resume_turn` must send replay items in ascending order as fixed user context before live tool-result history, force the existing `response_tools()` schema, and return the same validated `AgentTurn` shape as `next_turn`. `RecordedBackend.from_file_from_step` and `RecordedBackend.resume_turn` must consume only recorded turns beginning with the requested target step. The CLI loads `trace.json` and `checkpoints/` from the required `--baseline-run-dir`; it must reject a directory without both artifacts. The recorded command used by tests is `sieve resume --baseline-run-dir .verification-runs/phase1/baseline --step TSIEVE-T1-S002 --runs-dir .verification-runs/phase1/resumed --max-resumed-steps 20`, after the test creates `.verification-runs/phase1/baseline` through the production baseline runner. The live variant additionally accepts `--live --model gpt-5.6`; default mode must never use a live call.

## Files to create or modify

- **Reads:** `src/sieve/replay.py` — obtain frozen prior-step context from SIV-INT-001.
- **Reads:** `src/sieve/budget.py` — enforce the SIV-INT-004 guard.
- **Reads:** `src/sieve/runner.py` — reuse or extract existing workspace-safe action execution and unified-diff behavior.
- **Reads:** `src/sieve/persistence.py` — use canonical run-directory and trace-writing functions.
- **Reads:** `tasks/SIEVE-T1/recorded_run.json` — baseline recorded turn sequence and no-op replay source.
- **Writes (creates or modifies):** `src/sieve/agent.py` — resumable backend protocol and context-aware OpenAI/recorded implementations.
- **Writes (creates or modifies):** `src/sieve/runner.py` — additive per-step workspace checkpoints for future baseline runs.
- **Writes (creates or modifies):** `src/sieve/resume.py` — `ResumeRunner` and replay execution.
- **Writes (creates or modifies):** `src/sieve/cli.py` — exact `resume` subcommand and argument validation.
- **Writes (creates or modifies):** `tasks/SIEVE-T1/recorded_resume_run.json` — deterministic no-op replay turns beginning at `TSIEVE-T1-S002`.
- **Writes (creates or modifies):** `tests/test_agent.py` — mocked API resume request formation and recorded resume behavior.
- **Writes (creates or modifies):** `tests/test_runner.py` — baseline checkpoint persistence tests.
- **Writes (creates or modifies):** `tests/test_resume.py` — resume-runner system, validation, and budget integration tests.
- **Writes (creates or modifies):** `tests/test_cli.py` — `sieve resume` parsing and persisted-output tests.

## Implementation notes

The spec says, verbatim: “steps `1..k-1` are replayed as fixed context verbatim; step `k`'s target field is edited; generation resumes at step `k`.” In Phase 1, preserve the target field instead of editing it. The replay result must not copy the baseline’s old suffix or final diff: restore the checkpoint after `k-1`, generate and execute from `k` forward, then calculate the new unified diff against the pristine fixture through the same Phase 0 behavior. For the first target step, restore `checkpoints/initial/`. Do not reuse the baseline run directory or overwrite its `trace.json`; every replay is a new persisted run.

No-op replay uses `run_type="baseline"` and an empty `InterventionMetadata`, because §5.2 permits `perturbed` only for an actual intervention and Phase 1 explicitly has “no field edited.” Do not add a `replay` run type, a `replay_context` field, or any optional data-contract field. Persisted API tool-result pairing is Phase 2 SIV-SCH-002 and is out of scope.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_resume_runner_rejects_target_absent_from_baseline_trace`; `test_resume_runner_rejects_missing_pre_target_checkpoint`; `test_resume_runner_rejects_non_resumable_backend`; `test_recorded_backend_resume_starts_at_requested_step`; and `test_resume_runner_preserves_empty_baseline_intervention_metadata`. |
| Integration | `test_resume_runner_passes_siv_int_001_context_to_resumable_backend`: assert S001 JSON is passed before target S002. `test_resume_runner_persists_trace_through_canonical_persistence`: load written JSON with `TraceRecord.model_validate_json`. |
| System | `test_resume_sieve_t1_from_step_2_generates_complete_trace`: create a recorded baseline, assert `checkpoints/TSIEVE-T1-S001/` exists, then resume with recorded backend and mocked Vitest; assert the resumed trace contains S001 fixed context plus regenerated S002, has a new run directory, and has a final diff generated from the restored pre-target workspace. |
| Acceptance | N/A — the Phase 1 DoD comparison itself is intentionally owned by SIV-INT-003 so it remains an independently failing acceptance gate. |
| Smoke | `test_resume_runner_smoke_recorded_sieve_t1`: resume at S002 with a two-step budget, assert exit without exception and a `trace.json` exists. |
| Sanity | `test_resume_generated_step_ids_are_monotonic_and_task_owned`: assert returned steps validate §5.1 order and `TSIEVE-T1-S` ownership. |
| Regression | `test_recorded_resume_fixture_is_deterministic`: two recorded no-op resumes under mocked task tests produce byte-identical `final_diff` values; the golden equality assertion is added by SIV-INT-003. |
| End-to-end | `test_cli_resume_writes_new_trace_json`: invoke `sieve run --task SIEVE-T1 --runs-dir` with a temporary directory, parse the produced baseline run directory, then invoke `sieve resume --baseline-run-dir` with that exact directory, target `TSIEVE-T1-S002`, and a separate temporary resumed-runs directory; assert a new valid trace path is printed and exists. |
| API | `test_openai_resume_turn_sends_fixed_context_before_history_and_uses_response_tools`: mock `responses.create`, assert the request includes exact replay JSON before tool-result messages and validates its structured response. Live smoke is N/A — live Codex calls are manual and never CI-gated by §8. |
| UI | N/A — Phase 1 does not generate a static report; static report UI is Phase 4 scope. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_agent.py tests/test_runner.py tests/test_resume.py tests/test_cli.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new or modified files.
- [ ] No data contract in §5 was altered; replay output is a new valid §5.2 baseline trace with no added fields.
- [ ] The recorded resume fixture is committed with the code it characterizes.
