# SIV-RPT-003 — Honest Limitations in every report

Read `_PREAMBLE.md` first; it is binding for this implementation prompt.

## Traceability

- Phase: 4 — Full Suite & Report (SIEVE-SPEC.md §13)
- Requirement: Honest Limitations section embedded in every generated report
- Wave: 3
- Depends on: SIV-RPT-001, SIV-RPT-002
- Unblocks: SIV-OPS-003
- Advances DoD: ensures the rendered judge-facing artifact contains all required methodological limitations.

## Objective

Extend the existing static report renderer with a visible, semantic Honest Limitations section containing every limitation mandated by §11. The section must appear on every generated report regardless of score count or score values, so the report communicates the product’s behavioral-sensitivity scope without hiding caveats in documentation.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- This requirement reads report inputs only; it writes no §5 trace or score fields and must not introduce a report-only data contract.
- SIV-RPT-001 supplies the renderer and SIV-RPT-002 supplies the headline grid. Preserve both their data ordering, grid binning, static HTML, and no-network behavior.
- Risk §15: judges may conflate Sieve with a generic eval harness. The first limitation must say what behavioral insensitivity supports and explicitly disavow a mechanistic claim.

## Interface specification

```python
# src/sieve/reporting.py
HONEST_LIMITATIONS: tuple[str, str, str] = (
    "Behavioral insensitivity is evidence the stated reasoning wasn't necessary for that output — it is not a full mechanistic account of the model's internal computation.",
    "The structured schema is a deliberate simplification; Sieve audits faithfulness to a schema the model was told to fill out, not fully free-form chain-of-thought.",
    "Five tasks is a proof of concept, not a benchmark. The contribution is the intervention methodology and harness; the task suite is an illustrative first application.",
)

def render_honest_limitations() -> str: raise NotImplementedError
```

`render_honest_limitations()` must return a `<section id="honest-limitations" aria-labelledby="honest-limitations-heading">` with one `<h2>` exactly `Honest Limitations` and an ordered list of exactly the three constant strings, in the specified order. `render_report()` must include this section after the score table and before `</main>`. Do not make the section conditional, collapsible, remote-loaded, or editable from score input.

## Files to create or modify (this section is load-bearing for concurrency — see below)

- **Reads:** `SIEVE-SPEC.md` — §11 Honest Limitations text, §8 static-report requirement, and §10 UI taxonomy.
- **Reads:** `src/sieve/reporting.py` — report shell, 2×2 grid, and table rendered by SIV-RPT-001 and SIV-RPT-002.
- **Reads:** `tests/test_reporting.py` — existing report parsing and visual checks.
- **Reads:** `tests/fixtures/phase4/reporting/two-by-two-grid.html` — report layout baseline to preserve.
- **Writes (creates or modifies):** `src/sieve/reporting.py` — literal limitation constant, semantic renderer, and report inclusion.
- **Writes (creates or modifies):** `tests/test_reporting.py` — exact-text, order, unconditional-rendering, and accessibility tests.
- **Writes (creates or modifies):** `tests/fixtures/phase4/reporting/honest-limitations.html` — committed static section golden fixture.

## Implementation notes

The three limitations in §11 are binding and must be rendered verbatim:

1. Behavioral insensitivity is evidence the stated reasoning wasn't *necessary* for that output — it is not a full mechanistic account of the model's internal computation.
2. The structured schema is a deliberate simplification; Sieve audits faithfulness *to a schema the model was told to fill out*, not fully free-form chain-of-thought.
3. Five tasks is a proof of concept, not a benchmark. The contribution is the intervention methodology and harness; the task suite is an illustrative first application.

The Python constant is normalized only for the report’s plain-text representation; the rendered HTML must retain the §11 wording and emphasis semantically, using `<em>` around `necessary` and `to a schema the model was told to fill out`. Do not add claims about hidden reasoning, benchmarks, model safety, or statistical confidence. The section is not a substitute for the grid or table.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_render_honest_limitations_has_semantic_section_heading_ordered_list_and_exact_three_items`; `test_honest_limitations_constant_has_exact_spec_order_and_no_empty_item`. |
| Integration | `test_render_report_includes_limitations_after_grid_and_score_table_for_loaded_score_data` verifies report component composition. |
| System | `test_offline_recorded_score_batch_report_contains_limitations_without_live_api_call` runs the existing local score path through report rendering. |
| Acceptance | `test_phase4_generated_report_contains_all_three_verbatim_honest_limitations` proves the stated DoD clause. |
| Smoke | `test_honest_limitations_render_for_single_score_report_is_nonblank` checks the smallest valid report. |
| Sanity | `test_limitations_are_unconditional_unique_and_not_derived_from_score_values` renders distinct batches and compares the same section. |
| Regression | `test_honest_limitations_section_matches_committed_html_golden` compares the static section to `honest-limitations.html` with no live API call. |
| End-to-end | N/A — CLI report invocation belongs to SIV-OPS-003; this prompt owns static report composition. |
| API | N/A — literal local static content makes no Codex/GPT-5.6 API request. |
| UI | `test_rendered_report_exposes_visible_honest_limitations_heading_and_three_readable_list_items` parses the report artifact and asserts the §10 UI scope. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_reporting.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new and modified files.
- [ ] No data contract in §5 was altered; limitations are report literals, not new score data.
- [ ] Golden/regression fixtures, if authored, are committed with the code they characterize.
