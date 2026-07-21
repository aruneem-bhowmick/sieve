# SIV-SCH-002 — Pair raw tool-call results with trace steps

## Traceability
- Phase: 2 — Intervention Core (SIEVE-SPEC.md §13)
- Requirement: Pair every step with its raw tool-call result(s) in the trace
- Wave: 1
- Depends on: SIV-INT-001, SIV-INT-002, SIV-INT-003, SIV-INT-004
- Unblocks: SIV-INT-005, SIV-INT-006
- Advances DoD: makes each later baseline/perturbed record a human-comparable trace with the raw action outcome associated with every reasoning step.

## Objective

Add an additive, ordered raw-tool-result representation to Layer 1 and Layer 2 persisted traces. Every new baseline, no-op replay, and perturbed trace must persist exactly one raw local result beside each emitted reasoning step, allowing a reviewer to reconstruct which observable action followed each rationale without changing a locked §5.2 field.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read `TraceRecord.steps`, `TraceRecord.test_result`, and the new additive `TraceRecord.tool_results`; a supplied `tool_results[index]` pairs with `steps[index]`. Its fields are `name: PlannedAction`, `target: str`, `output: str`, and `succeeded: bool`.
- SIV-INT-002 already supplies `TaskRunner._execute_turn`, `ResumeRunner`, and canonical trace persistence. Preserve their Phase 1 no-op semantics and final-diff equality.
- The relevant §15 risk is live API nondeterminism. All tests in this prompt use recorded backends or mocked API responses; do not make a live request in CI.

## Interface specification

```python
# src/sieve/schemas.py
class ToolResultRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: PlannedAction
    target: str
    output: str
    succeeded: bool

class TraceRecord(BaseModel):
    # Existing fields are unchanged.
    tool_results: list[ToolResultRecord] = Field(default_factory=list)
    # If tool_results was explicitly supplied, validate len(tool_results) == len(steps).
    # If it was omitted, accept the trace as a legacy Phase 0/1 artifact.

# src/sieve/agent.py
# Import ToolResultRecord from sieve.schemas and use it as the single tool-result
# value type in CodingAgentBackend and ResumableCodingAgentBackend histories.

# src/sieve/runner.py and src/sieve/resume.py
# Keep `tool_results: list[ToolResultRecord]`; append the result returned from
# every successful or failed local action in the same iteration that appends its step;
# pass tool_results=tool_results when constructing every new TraceRecord.
```

`ToolResultRecord.output` is the raw UTF-8 observable output already captured by `_execute_turn`: file contents for `read_file`, `"edited"` for `edit_file`, newline-joined paths for `search`, and stdout plus stderr for command/test actions. Do not replace it with a summary or redact it. A failure is still a raw result and must be paired with its step.

## Files to create or modify

- **Reads:** `src/sieve/schemas.py` — preserve the locked trace and step models while adding one optional field.
- **Reads:** `src/sieve/agent.py` — retain backend history serialization and import direction.
- **Reads:** `src/sieve/runner.py` — capture local action results for baselines.
- **Reads:** `src/sieve/resume.py` — capture local action results for no-op replays.
- **Reads:** `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` — prove omitted additive data remains backward-compatible.
- **Writes (creates or modifies):** `src/sieve/schemas.py` — add `ToolResultRecord`, additive `tool_results`, and supplied-list cardinality validation.
- **Writes (creates or modifies):** `src/sieve/agent.py` — replace the duplicate dataclass result type with the schema-owned record type without changing backend request semantics.
- **Writes (creates or modifies):** `src/sieve/runner.py` — populate and persist baseline tool-result pairs.
- **Writes (creates or modifies):** `src/sieve/resume.py` — populate and persist replay tool-result pairs.
- **Writes (creates or modifies):** `tests/test_schemas.py` — validate pair shape, cardinality, order, and legacy omission.
- **Writes (creates or modifies):** `tests/test_runner.py` — assert recorded baseline pairs are persisted with matching result fields.
- **Writes (creates or modifies):** `tests/test_resume.py` — assert no-op replay pairs are persisted in the regenerated suffix trace.
- **Writes (creates or modifies):** `tests/test_agent.py` — update protocol/history assertions to use `ToolResultRecord`.
- **Writes (creates or modifies):** `tests/fixtures/phase2/SIEVE-T1-tool-result-pairs.json` — record the expected ordered raw results for the deterministic SIEVE-T1 baseline.

## Implementation notes

The binding sentence is: “Every step is paired with the raw tool-call result(s) that followed it (SIV-SCH-002).” Pairing is positional because one `AgentTurn` has exactly one action and `TaskRunner._execute_turn` returns exactly one result. Do not add a separate run type, change `steps` into objects, or alter the JSON meaning of any §5.2 field. `tool_results` is additive only.

Callers creating a new trace must explicitly provide `tool_results`, so the validator rejects an explicitly supplied list whose length differs from `steps`. Omission is accepted only to load previously persisted Phase 0/1 JSON; this is required by §5’s additive-only rule. `TraceRecord.model_dump_json()` for new runner/resume traces must include the populated list.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_trace_accepts_ordered_tool_result_records`; `test_trace_rejects_explicit_tool_result_count_mismatch`; `test_tool_result_record_rejects_unknown_fields`; and `test_legacy_phase1_trace_without_tool_results_validates`. Assert names, targets, outputs, and booleans survive `model_dump_json`/`model_validate_json`. |
| Integration | `test_runner_persists_step_result_pairs_through_canonical_write_trace` and `test_resume_persists_step_result_pairs_through_canonical_write_trace`: load each `trace.json`, assert equal step/result lengths and that the S002 `run_tests` result has the matching action target. |
| System | `test_recorded_sieve_t1_baseline_writes_raw_result_pair_for_each_step`: execute the unmocked production `TaskRunner` against the recorded backend and the actual SIEVE-T1 fixture test command; assert both paired results and a valid `trace.json`. |
| Acceptance | N/A — the Phase 2 pair-and-metadata acceptance case requires a real intervention and is owned by SIV-INT-005 and SIV-INT-006. |
| Smoke | `test_tool_result_pairing_smoke_recorded_sieve_t1`: run one recorded SIEVE-T1 baseline and assert `len(trace.tool_results) == len(trace.steps) == 2`. |
| Sanity | `test_persisted_tool_result_pair_order_matches_step_action_order`: assert every `step.planned_action == result.name` and `step.action_target == result.target` in the deterministic fixture trace. |
| Regression | `test_recorded_sieve_t1_tool_result_pairs_match_phase2_golden_fixture`: compare the normalized list of four raw result fields with `tests/fixtures/phase2/SIEVE-T1-tool-result-pairs.json`; no live API call is permitted. |
| End-to-end | `test_cli_run_trace_contains_raw_tool_result_pairs`: invoke `sieve run --task SIEVE-T1 --runs-dir tmp_path / "runs"` and load the printed `trace.json`, asserting paired lists and the expected S002 test result. |
| API | `test_openai_history_serializes_tool_result_record_verbatim`: mock the Responses client, pass a `ToolResultRecord` containing stdout/stderr text to `next_turn`, and assert the resulting history JSON preserves all four result fields. Live smoke is N/A — §8 prohibits CI-gated live calls. |
| UI | N/A — no static HTML report exists before Phase 4, and this requirement produces JSON evidence only. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_schemas.py tests/test_agent.py tests/test_runner.py tests/test_resume.py tests/test_cli.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new or modified files.
- [ ] No existing §5 field was altered; `tool_results` is additive and legacy Phase 0/1 JSON still validates when it omits the field.
- [ ] The golden raw-result fixture is committed with the code it characterizes.
