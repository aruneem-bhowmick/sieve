# SIV-RPT-002 — Headline 2×2 grid visual

Read `_PREAMBLE.md` first; it is binding for this implementation prompt.

## Traceability

- Phase: 4 — Full Suite & Report (SIEVE-SPEC.md §13)
- Requirement: 2×2 grid visual (§7.3) as the headline element
- Wave: 2
- Depends on: SIV-RPT-001
- Unblocks: SIV-RPT-003, SIV-OPS-003
- Advances DoD: makes the judge-facing report immediately communicate the aggregate causal-audit outcomes.

## Objective

Extend the SIV-RPT-001 static report so the first substantive report element is a legible 2×2 summary of all scored perturbed runs. Each paired score/trace entry contributes exactly once to bins defined by patch divergence and whether that perturbed run's tests pass or break, while the existing detailed table remains a complete audit trail.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read `ReportEntry.score.patch_divergence` and `ReportEntry.perturbed_test_result.failed` through `ReportData`; `patch_divergence == 0.0` means unchanged, `patch_divergence > 0.0` means changed, and an empty perturbed `failed` list means tests still pass while a non-empty list means tests broke. The table continues to render the separate locked `outcome_stability` field.
- SIV-RPT-001 provides `ReportData`, deterministic rendering, `id="two-by-two-grid"`, and its report fixtures. Modify that module rather than creating a second renderer.
- Risk §15: judges may confuse the product with an eval harness. The grid must lead with causal outcome categories and concise count labels, not model prose or text-similarity claims.

## Interface specification

```python
# src/sieve/reporting.py
from collections.abc import Sequence
from dataclasses import dataclass

# ReportEntry is defined earlier in this same module by SIV-RPT-001.

@dataclass(frozen=True)
class TwoByTwoCounts:
    unchanged_pass: int
    unchanged_broke: int
    changed_pass: int
    changed_broke: int

def summarize_two_by_two(entries: Sequence[ReportEntry]) -> TwoByTwoCounts: raise NotImplementedError
def render_two_by_two_grid(counts: TwoByTwoCounts) -> str: raise NotImplementedError
```

Merge these exact members into the existing `package.json` objects:

```json
{
  "scripts": {"report:screenshot": "node tools/render_report_screenshot.mjs"},
  "devDependencies": {"playwright": "1.52.0"}
}
```

`summarize_two_by_two()` must reject an entry whose `score.patch_divergence` is outside `[0.0, 1.0]`, even if passed through an untyped caller. It assigns zero exactly to `unchanged_*`; every positive value is `changed_*`. It assigns an empty `entry.perturbed_test_result.failed` list to `*_pass` and a non-empty list to `*_broke`. `render_two_by_two_grid()` returns semantic HTML using a `<section id="two-by-two-grid" aria-labelledby="two-by-two-heading">`, one `<h2>`, and exactly four labeled `<article>` cells with deterministic ids `unchanged-pass`, `unchanged-broke`, `changed-pass`, and `changed-broke`. `render_report()` must replace its Wave 1 empty container with this grid before the score table and must embed self-contained CSS that makes four cells visible without JavaScript.

## Files to create or modify (this section is load-bearing for concurrency — see below)

- **Reads:** `SIEVE-SPEC.md` — §7.2, §7.3, §10 UI row, and §11 artifact requirement.
- **Reads:** `src/sieve/reporting.py` — SIV-RPT-001 renderer and extension container.
- **Reads:** `tests/test_reporting.py` — existing report data and table behavior.
- **Reads:** `tests/fixtures/phase4/reporting/two-score-runs/` — score inputs for deterministic rendering.
- **Reads:** `package.json` and `package-lock.json` — root `report:screenshot` command and locked Playwright development dependency added by this prompt.
- **Writes (creates or modifies):** `src/sieve/reporting.py` — grid count model, binning, markup, and self-contained visual styles.
- **Writes (creates or modifies):** `tests/test_reporting.py` — grid unit, integration, accessibility, and rendering tests.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/two-by-two-grid.html` — deterministic grid golden fixture.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/two-by-two-grid.png` — manually reviewed static screenshot baseline generated from the fixture report.
- **Writes (creates or modifies):** `package.json` — add exactly `"report:screenshot": "node tools/render_report_screenshot.mjs"` and the pinned development dependency `"playwright": "1.52.0"`.
- **Writes (creates or modifies):** `package-lock.json` — lock the Playwright development dependency.
- **Writes (creates or modifies):** `tools/render_report_screenshot.mjs` — Playwright Chromium renderer accepting `--input <html-path>` and `--output <png-path>` with a fixed `1280x900` viewport, local `file:` input only, and no network requests.

## Implementation notes

§7.3 states: “Reported alongside `outcome_stability` as a 2×2: {patch changed / unchanged} × {tests still pass / broke}. This 2×2 is the headline visual (SIV-RPT-002) — legible to a non-specialist in five seconds.” Use the exact user-visible axes `Patch unchanged`/`Patch changed` and `Tests still pass`/`Tests broke`. `outcome_stability` remains visible in the per-task table; it is not the grid's absolute pass/broke axis. SIV-RPT-001 supplies the perturbed `TestResult` needed to derive that axis without changing a §5 contract.

The counts must sum to `len(entries)`. Never derive bins from `faithfulness_score`; although it is currently equal to patch divergence, the grid explicitly represents the two source measures. Do not add tool-path divergence, external JavaScript to the generated report, a report build step, charts, or a network dependency.

For the required manual-reviewed screenshot regression, add `npm run report:screenshot -- --input tests/fixtures/phase4/reporting/two-by-two-grid.html --output .verification-runs/phase4/two-by-two-grid.actual.png`. Before the manual check, install the pinned browser once with `npx playwright install chromium`. A reviewer must compare that exact output at the fixed viewport to committed `two-by-two-grid.png` and record pass/fail in the executor report. This renderer is a development-only verification tool; the generated `report.html` remains a standalone local static file with no runtime dependency.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_summarize_two_by_two_places_zero_and_positive_divergence_with_passing_and_broken_perturbed_tests_in_correct_cells`; `test_summarize_two_by_two_rejects_out_of_range_untyped_values`; `test_render_two_by_two_grid_has_exactly_four_labeled_cells_and_counts`. |
| Integration | `test_render_report_inserts_grid_before_existing_score_table_and_counts_every_loaded_paired_entry_once` verifies the score/trace-data→report handoff. |
| System | `test_offline_recorded_score_batch_with_actual_perturbed_test_results_renders_grid_with_counts_equal_to_batch_size` scores a deterministic batch then renders the full report. |
| Acceptance | `test_phase4_report_headline_grid_is_legible_and_complete_for_all_four_patch_and_test_outcome_categories` asserts each category and count appears in the generated artifact. |
| Smoke | `test_two_by_two_grid_smoke_one_unchanged_passing_entry_renders_nonblank_cell` exercises the smallest report input. |
| Sanity | `test_grid_counts_sum_to_input_count_and_no_entry_appears_in_multiple_bins` catches degenerate or duplicate classification. |
| Regression | `test_two_by_two_grid_markup_matches_committed_golden`; manual regression: run the exact `npm run report:screenshot` command above, compare its fixed-viewport PNG to `two-by-two-grid.png`, and record the review result without a live API call. |
| End-to-end | N/A — the report CLI belongs to SIV-OPS-003; this requirement modifies renderer output only. |
| API | N/A — a static grid over local score records makes no Codex/GPT-5.6 API request. |
| UI | `test_static_report_has_four_visible_grid_cells_with_heading_readable_count_text_and_the_exact_tests_pass_or_broke_labels`; manual fixed-viewport screenshot review uses the declared Playwright command and committed PNG baseline. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All automated non-N/A tests in this prompt pass locally via `python -m pytest -v --no-cov tests/test_reporting.py`. Run the exact manual screenshot command from the Regression/UI test row and record the visual-comparison result.
- [ ] `python -m mypy --strict src/sieve/reporting.py tests/test_reporting.py`, `python -m ruff check src/sieve/reporting.py tests/test_reporting.py`, and `python -m black --check src/sieve/reporting.py tests/test_reporting.py` pass.
- [ ] The full-project gate (`python -m pytest -v`, `python -m ruff check .`, `python -m black --check .`, and `python -m mypy --strict .`) is owned by the mandatory Wave 2 integration checkpoint in `WAVES.md`; its duration must not be reported as an executor deviation.
- [ ] No data contract in §5 was altered; binning reads only existing score and perturbed-trace fields.
- [ ] Golden/regression fixtures, if authored, are committed with the code they characterize.
