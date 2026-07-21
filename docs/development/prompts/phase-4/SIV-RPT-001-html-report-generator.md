# SIV-RPT-001 — HTML report generator

Read `_PREAMBLE.md` first; it is binding for this implementation prompt.

## Traceability

- Phase: 4 — Full Suite & Report (SIEVE-SPEC.md §13)
- Requirement: HTML report generator: reads all score records in `runs/`, renders 2×2 + table
- Wave: 1
- Depends on: Phase 3
- Unblocks: SIV-RPT-002, SIV-RPT-003, SIV-OPS-003
- Advances DoD: creates the static `report.html` artifact and its complete per-task/per-intervention score table.

## Objective

Implement the Layer 3 static report generator that discovers each persisted score artifact and its sibling perturbed trace under `runs/`, validates the locked §5.2 and §5.3 models, deterministically renders a single self-contained HTML document, and includes one table row for every score. This first report prompt owns paired artifact loading, row rendering, document shell, and report-file persistence; the headline visual and limitations content are deliberately added by later prompts.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read `ScoreRecord.task_id`, `intervention_type`, `patch_divergence`, `outcome_stability`, and `faithfulness_score`, plus the sibling perturbed `TraceRecord.test_result.passed` and `TraceRecord.test_result.failed`; do not add fields or infer data from a live API.
- `ScoreRunner` writes each validated score to `runs/<perturbed_run_id>/score.json`, and that same directory contains the paired perturbed `trace.json`. Phase 3 fixtures are valid inputs; duplicate `(task_id, intervention_type)` records must be rejected rather than silently overwritten.
- SIV-RPT-002 owns the rendered 2×2 grid markup and styling, and SIV-RPT-003 owns the Honest Limitations section. Keep extension points explicit but do not add either feature here.
- Risk §15: judges may confuse Sieve with an ordinary eval harness. Make the table legible and show both artifact divergence and outcome stability so the causal-audit result is concrete.

## Interface specification

```python
# src/sieve/reporting.py
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sieve.schemas import ScoreRecord, TestResult

@dataclass(frozen=True)
class ReportEntry:
    score: ScoreRecord
    perturbed_test_result: TestResult

@dataclass(frozen=True)
class ReportData:
    entries: Sequence[ReportEntry]

class ReportDataError(ValueError):
    pass

def load_report_data(runs_dir: Path) -> ReportData: raise NotImplementedError
def render_report(data: ReportData) -> str: raise NotImplementedError
def write_report(runs_dir: Path, output_path: Path) -> Path: raise NotImplementedError
```

`load_report_data()` must recursively discover only `score.json` files whose parent is a direct `runs/<run_id>/` directory. For each score, parse `score.json` as `ScoreRecord` and its sibling `trace.json` as `TraceRecord`; reject malformed JSON, invalid records, a non-perturbed sibling trace, a sibling trace whose `task_id` differs from the score, a sibling trace whose `intervention.type` differs from the score, duplicate `(task_id, intervention_type)` keys, a missing sibling trace, and a directory with no score records. It returns entries in ascending `(entry.score.task_id, entry.score.intervention_type)` order. `render_report()` returns complete UTF-8 HTML with no external network assets, a title, a score table with exactly the columns `Task`, `Intervention`, `Patch divergence`, `Outcome stability`, and `Faithfulness score`, and an empty `id="two-by-two-grid"` extension container. `write_report()` writes atomically to the exact caller-supplied `output_path`, creates its parent directory, and returns that path. It must not write a trace, diff, or score artifact outside `runs/<run_id>/`.

## Files to create or modify (this section is load-bearing for concurrency — see below)

- **Reads:** `SIEVE-SPEC.md` — §5.3, §7.2–§7.3, §8, §10, and §11 report requirements.
- **Reads:** `src/sieve/schemas.py` — canonical `ScoreRecord`, `TraceRecord`, and `TestResult` validation.
- **Reads:** `src/sieve/persistence.py` — canonical score path convention.
- **Reads:** `tests/fixtures/phase3/t1-int01/expected-score.json` and `tests/fixtures/phase3/t3-int02/expected-score.json` — valid representative score inputs.
- **Writes (creates or modifies):** `src/sieve/reporting.py` — report data loading, deterministic HTML table rendering, and atomic writer.
- **Writes (creates or modifies):** `tests/test_reporting.py` — report data, table, persistence, integration, and output validation tests.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/two-score-runs/00000000-0000-0000-0000-000000000041/score.json` — valid score fixture.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/two-score-runs/00000000-0000-0000-0000-000000000041/trace.json` — matching valid perturbed trace fixture.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/two-score-runs/00000000-0000-0000-0000-000000000042/score.json` — valid score fixture.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/two-score-runs/00000000-0000-0000-0000-000000000042/trace.json` — matching valid perturbed trace fixture.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/expected-table.html` — stable table-body golden fixture.

## Implementation notes

The §5.3 contract is exactly `task_id`, `intervention_type`, `patch_divergence`, `outcome_stability`, and `faithfulness_score`. Faithfulness is “`faithfulness_score = patch_divergence   // primary`.” Display numeric fields with a fixed three-decimal representation without round-tripping or recalculating values. Escape every value inserted into HTML. A report generator must be deterministic: identical score files yield byte-identical HTML.

The table must label the score boolean only as `Outcome stability` with values `stable` or `changed`; that value remains the §5.3 set-equality result and is not an absolute test status. SIV-RPT-002 receives each entry's sibling perturbed `TestResult` and will derive the spec's grid axis exactly: `tests still pass` when `perturbed_test_result.failed == []`, otherwise `tests broke`. This uses existing §5.2 data and introduces no data-contract field or ADR.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_load_report_data_sorts_paired_entries_and_rejects_empty_invalid_duplicate_nested_missing_or_mismatched_artifacts`; `test_render_report_escapes_values_formats_numbers_and_has_exact_table_columns`; `test_write_report_creates_parent_and_writes_exact_html`. |
| Integration | `test_report_loader_consumes_phase3_score_json_and_sibling_perturbed_trace_artifacts_and_renderer_preserves_all_contract_fields` verifies the Layer 3 persisted score/trace→report handoff. |
| System | `test_recorded_t1_and_t3_scoring_then_write_report_produces_paired_entries_and_table_for_both_scores` uses the existing offline scoring path and report writer without a live API call. |
| Acceptance | `test_phase4_report_generator_renders_one_row_per_input_score_and_a_static_html_document` asserts the Phase 4 report-table portion of the DoD. |
| Smoke | `test_write_report_smoke_for_one_score_is_nonblank_and_exits_without_network` creates one fixture score and checks the file. |
| Sanity | `test_report_table_has_no_duplicate_task_intervention_rows_all_scores_are_in_range_and_each_entry_has_a_perturbed_test_result` validates paired inputs and rendered row uniqueness. |
| Regression | `test_two_score_report_table_matches_expected_table_golden` compares the stable table body against `expected-table.html` with no live call. |
| End-to-end | N/A — the report generator has no CLI until SIV-OPS-003 owns `sieve run-suite`; direct writer coverage keeps this prompt independent. |
| API | N/A — reading local score JSON and rendering static HTML makes no Codex/GPT-5.6 API request. |
| UI | `test_rendered_report_is_parseable_nonblank_html_and_table_row_count_equals_input_score_count` parses the artifact and asserts the narrow §10 report UI behavior. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_reporting.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new and modified files.
- [ ] No data contract in §5 was altered; report data is a read-only projection of existing score records and sibling perturbed trace records.
- [ ] Golden/regression fixtures, if authored, are committed with the code they characterize.
