"""Phase 4 static-report coverage for SIV-RPT-001."""

from __future__ import annotations

import json
import shutil
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from sieve.reporting import (
    HONEST_LIMITATIONS,
    ReportData,
    ReportDataError,
    ReportEntry,
    TwoByTwoCounts,
    load_report_data,
    render_honest_limitations,
    render_report,
    render_two_by_two_grid,
    select_representative_evidence,
    summarize_two_by_two,
    write_report,
)
from sieve.schemas import InterventionMetadata, ScoreRecord, TestResult, TraceRecord
from sieve.scoring import ScoreRunner

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
REPORT_FIXTURES = FIXTURES / "phase4" / "reporting"


def _copy_score_runs(destination: Path) -> Path:
    runs = destination / "runs"
    shutil.copytree(REPORT_FIXTURES / "two-score-runs", runs)
    return runs


def _table_body(html: str) -> str:
    return html.split("<tbody>\n", maxsplit=1)[1].split(
        "\n        </tbody>", maxsplit=1
    )[0]


def _section_markup(document: str, section_id: str) -> str:
    start = document.index(f'<section id="{section_id}"')
    end = document.index("</section>", start) + len("</section>")
    return document[start:end]


def _recorded_score_pair(runs: Path, name: str) -> ScoreRecord:
    fixture = FIXTURES / "phase3" / name
    baseline = TraceRecord.model_validate_json(
        (fixture / "baseline-trace.json").read_text(encoding="utf-8")
    )
    perturbed = TraceRecord.model_validate_json(
        (fixture / "perturbed-trace.json").read_text(encoding="utf-8")
    )
    for label, trace in (("baseline", baseline), ("perturbed", perturbed)):
        run_dir = runs / str(trace.run_id)
        run_dir.mkdir(parents=True)
        shutil.copy2(fixture / f"{label}-trace.json", run_dir / "trace.json")
        shutil.copytree(fixture / f"{label}-workspace", run_dir / "workspace")
    _, score = ScoreRunner(runs).score(baseline.run_id, perturbed.run_id)
    return score


def _entry(divergence: float, failed: list[str]) -> ReportEntry:
    score = ScoreRecord(
        task_id="SIEVE-T1",
        intervention_type="INT-01",
        patch_divergence=divergence,
        outcome_stability=not failed,
        faithfulness_score=divergence,
    )
    return ReportEntry(
        score, TestResult(passed=[] if failed else ["vitest"], failed=failed)
    )


def _four_category_data() -> ReportData:
    return ReportData(
        (
            _entry(0.0, []),
            _entry(0.0, ["vitest"]),
            _entry(0.25, []),
            _entry(1.0, ["vitest"]),
        )
    )


def test_load_report_data_sorts_paired_entries_and_rejects_empty_invalid_duplicate_nested_missing_or_mismatched_artifacts(  # noqa: E501
    tmp_path: Path,
) -> None:
    with pytest.raises(ReportDataError, match="no score records"):
        load_report_data(tmp_path / "empty")

    runs = _copy_score_runs(tmp_path)
    data = load_report_data(runs)
    assert [
        (entry.score.task_id, entry.score.intervention_type) for entry in data.entries
    ] == [
        ("SIEVE-T1", "INT-01"),
        ("SIEVE-T3", "INT-02"),
    ]
    assert data.entries[0].perturbed_test_result.failed == []

    (runs / "nested" / "run").mkdir(parents=True)
    shutil.copy2(
        runs / "00000000-0000-0000-0000-000000000041" / "score.json",
        runs / "nested" / "run" / "score.json",
    )
    assert len(load_report_data(runs).entries) == 2

    score_path = runs / "00000000-0000-0000-0000-000000000041" / "score.json"
    score_path.write_text("not json", encoding="utf-8")
    with pytest.raises(ReportDataError, match="invalid score"):
        load_report_data(runs)
    shutil.copy2(
        REPORT_FIXTURES
        / "two-score-runs"
        / "00000000-0000-0000-0000-000000000041"
        / "score.json",
        score_path,
    )
    invalid_score = json.loads(score_path.read_text(encoding="utf-8"))
    invalid_score["patch_divergence"] = 2.0
    score_path.write_text(json.dumps(invalid_score), encoding="utf-8")
    with pytest.raises(ReportDataError, match="invalid score"):
        load_report_data(runs)
    shutil.copy2(
        REPORT_FIXTURES
        / "two-score-runs"
        / "00000000-0000-0000-0000-000000000041"
        / "score.json",
        score_path,
    )

    duplicate = runs / "00000000-0000-0000-0000-000000000043"
    shutil.copytree(runs / "00000000-0000-0000-0000-000000000041", duplicate)
    duplicate_trace_path = duplicate / "trace.json"
    duplicate_trace = json.loads(duplicate_trace_path.read_text(encoding="utf-8"))
    duplicate_trace["run_id"] = duplicate.name
    duplicate_trace_path.write_text(json.dumps(duplicate_trace), encoding="utf-8")
    with pytest.raises(ReportDataError, match="duplicate"):
        load_report_data(runs)
    shutil.rmtree(duplicate)

    trace_path = runs / "00000000-0000-0000-0000-000000000041" / "trace.json"
    trace_path.unlink()
    with pytest.raises(ReportDataError, match="invalid trace"):
        load_report_data(runs)
    shutil.copy2(
        REPORT_FIXTURES
        / "two-score-runs"
        / "00000000-0000-0000-0000-000000000041"
        / "trace.json",
        trace_path,
    )

    mismatched = json.loads(trace_path.read_text(encoding="utf-8"))
    mismatched["task_id"] = "SIEVE-T99"
    mismatched["steps"][0]["step_id"] = "TSIEVE-T99-S001"
    trace_path.write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(ReportDataError, match="task IDs differ"):
        load_report_data(runs)
    shutil.copy2(
        REPORT_FIXTURES
        / "two-score-runs"
        / "00000000-0000-0000-0000-000000000041"
        / "trace.json",
        trace_path,
    )

    nonperturbed = json.loads(trace_path.read_text(encoding="utf-8"))
    nonperturbed["run_type"] = "baseline"
    nonperturbed["intervention"] = {
        "type": None,
        "target_step_id": None,
        "target_field": None,
        "original_value": None,
        "replacement_value": None,
    }
    trace_path.write_text(json.dumps(nonperturbed), encoding="utf-8")
    with pytest.raises(ReportDataError, match="not perturbed"):
        load_report_data(runs)
    shutil.copy2(
        REPORT_FIXTURES
        / "two-score-runs"
        / "00000000-0000-0000-0000-000000000041"
        / "trace.json",
        trace_path,
    )

    intervention_mismatch = json.loads(trace_path.read_text(encoding="utf-8"))
    intervention_mismatch["intervention"]["type"] = "INT-02"
    trace_path.write_text(json.dumps(intervention_mismatch), encoding="utf-8")
    with pytest.raises(ReportDataError, match="interventions differ"):
        load_report_data(runs)


def test_render_report_escapes_values_formats_numbers_and_has_exact_table_columns() -> (
    None
):
    score = ScoreRecord(
        task_id='SIEVE-<&"T1',
        intervention_type="INT-01",
        patch_divergence=0.5,
        outcome_stability=True,
        faithfulness_score=0.5,
    )
    html = render_report(
        ReportData((ReportEntry(score, TestResult(passed=["one"], failed=[])),))
    )
    assert "SIEVE-&lt;&amp;&quot;T1" in html
    assert "0.500" in html
    assert (
        "<thead><tr><th>Task</th><th>Intervention</th><th>Patch divergence</th>"
        "<th>Perturbed tests</th><th>Outcome stability</th>"
        "<th>Faithfulness score</th></tr></thead>"
    ) in html
    assert '<section id="two-by-two-grid"' in html


def test_report_rows_have_stable_fragment_anchors_for_evidence_references() -> None:
    faithful = ScoreRecord(
        task_id="SIEVE-T3",
        intervention_type="INT-02",
        patch_divergence=0.025,
        outcome_stability=False,
        faithfulness_score=0.025,
    )
    rendered = render_report(
        ReportData((ReportEntry(faithful, TestResult(passed=[], failed=["vitest"])),))
    )
    assert '<tr id="score-SIEVE-T3-INT-02">' in rendered


def test_curated_examples_link_to_each_frozen_trace_score_and_report_row() -> None:
    document = (ROOT / "docs" / "build-week" / "evidence.md").read_text(
        encoding="utf-8"
    )
    for evidence_path in (
        "../../tests/fixtures/phase3/t3-int02/baseline-trace.json",
        "../../tests/fixtures/phase3/t3-int02/perturbed-trace.json",
        "../../tests/fixtures/phase3/t3-int02/expected-score.json",
        "../../tests/fixtures/phase3/t1-int01/baseline-trace.json",
        "../../tests/fixtures/phase3/t1-int01/perturbed-trace.json",
        "../../tests/fixtures/phase3/t1-int01/expected-score.json",
    ):
        assert f"]({evidence_path})" in document
    for anchor in ("score-SIEVE-T3-INT-02", "score-SIEVE-T1-INT-01"):
        assert f"#{anchor})" in document
        assert f'id="{anchor}"' in (REPORT_FIXTURES / "expected-table.html").read_text(
            encoding="utf-8"
        )


def test_write_report_creates_parent_and_writes_exact_html(tmp_path: Path) -> None:
    runs = _copy_score_runs(tmp_path)
    output = tmp_path / "nested" / "report.html"
    assert write_report(runs, output) == output
    assert output.read_text(encoding="utf-8") == render_report(load_report_data(runs))


def test_report_loader_consumes_phase3_score_json_and_sibling_perturbed_trace_artifacts_and_renderer_preserves_all_contract_fields(  # noqa: E501
    tmp_path: Path,
) -> None:
    runs = _copy_score_runs(tmp_path)
    score_path = runs / "00000000-0000-0000-0000-000000000041" / "score.json"
    score_path.write_text(
        (FIXTURES / "phase3" / "t1-int01" / "expected-score.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    rendered = render_report(load_report_data(runs))
    for value in ("SIEVE-T1", "INT-01", "0.000", "Tests pass"):
        assert value in rendered


def test_recorded_t1_and_t3_scoring_then_write_report_produces_paired_entries_and_table_for_both_scores(  # noqa: E501
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    expected_scores = [
        _recorded_score_pair(runs, name) for name in ("t1-int01", "t3-int02")
    ]
    output = tmp_path / "report.html"
    write_report(runs, output)
    assert [entry.score for entry in load_report_data(runs).entries] == expected_scores
    assert _table_body(output.read_text(encoding="utf-8")).count("<tr") == 2


def test_phase4_report_generator_renders_one_row_per_input_score_and_a_static_html_document(  # noqa: E501
    tmp_path: Path,
) -> None:
    data = load_report_data(_copy_score_runs(tmp_path))
    rendered = render_report(data)
    assert rendered.startswith("<!doctype html>")
    assert _table_body(rendered).count("<tr") == len(data.entries)


def test_write_report_smoke_for_one_score_is_nonblank_and_exits_without_network(
    tmp_path: Path,
) -> None:
    runs = _copy_score_runs(tmp_path)
    shutil.rmtree(runs / "00000000-0000-0000-0000-000000000042")
    output = write_report(runs, tmp_path / "report.html")
    assert output.stat().st_size > 0


def test_report_table_has_no_duplicate_task_intervention_rows_all_scores_are_in_range_and_each_entry_has_a_perturbed_test_result(  # noqa: E501
    tmp_path: Path,
) -> None:
    data = load_report_data(_copy_score_runs(tmp_path))
    keys = [
        (entry.score.task_id, entry.score.intervention_type) for entry in data.entries
    ]
    assert len(keys) == len(set(keys))
    assert all(0.0 <= entry.score.faithfulness_score <= 1.0 for entry in data.entries)
    assert all(
        isinstance(entry.perturbed_test_result, TestResult) for entry in data.entries
    )


def test_two_score_report_table_matches_expected_table_golden(tmp_path: Path) -> None:
    actual = _table_body(render_report(load_report_data(_copy_score_runs(tmp_path))))
    expected = (
        (REPORT_FIXTURES / "expected-table.html").read_text(encoding="utf-8").rstrip()
    )
    assert actual == expected


def test_rendered_report_is_parseable_nonblank_html_and_table_row_count_equals_input_score_count(  # noqa: E501
    tmp_path: Path,
) -> None:
    class _Parser(HTMLParser):
        pass

    data = load_report_data(_copy_score_runs(tmp_path))
    rendered = render_report(data)
    parser = _Parser()
    parser.feed(rendered)
    parser.close()
    assert rendered.strip()
    assert _table_body(rendered).count("<tr") == len(data.entries)


def test_summarize_two_by_two_places_zero_and_positive_divergence_with_passing_and_broken_perturbed_tests_in_correct_cells() -> (  # noqa: E501
    None
):
    assert summarize_two_by_two(_four_category_data().entries) == TwoByTwoCounts(
        unchanged_pass=1,
        unchanged_broke=1,
        changed_pass=1,
        changed_broke=1,
    )


def test_summarize_two_by_two_rejects_out_of_range_untyped_values() -> None:
    invalid_entry = cast(
        ReportEntry,
        SimpleNamespace(
            score=SimpleNamespace(patch_divergence=1.01),
            perturbed_test_result=TestResult(passed=["vitest"], failed=[]),
        ),
    )
    with pytest.raises(ValueError, match="patch_divergence"):
        summarize_two_by_two((invalid_entry,))


def test_representative_evidence_selection_is_deterministic_and_escapes_trace_metadata() -> (  # noqa: E501
    None
):
    unfaithful = ReportEntry(
        ScoreRecord(
            task_id="SIEVE-<&T1",
            intervention_type="INT-01",
            patch_divergence=0.0,
            outcome_stability=True,
            faithfulness_score=0.0,
        ),
        TestResult(passed=["vitest"], failed=[]),
        InterventionMetadata(
            type="INT-01",
            target_step_id="TSIEVE-T1-S001",
            target_field="claim",
            original_value="<original>",
            replacement_value="",
        ),
        "<diff>",
    )
    sensitive = ReportEntry(
        ScoreRecord(
            task_id="SIEVE-T3",
            intervention_type="INT-02",
            patch_divergence=0.5,
            outcome_stability=False,
            faithfulness_score=0.5,
        ),
        TestResult(passed=[], failed=["vitest"]),
        InterventionMetadata(
            type="INT-02",
            target_step_id="TSIEVE-T3-S001",
            target_field="constraint",
            original_value="Keep @",
            replacement_value="Keep #",
        ),
        "changed",
    )
    data = ReportData((unfaithful, sensitive))

    selected = select_representative_evidence(data.entries)

    assert [(item.kind, item.entry.score.task_id) for item in selected] == [
        ("reasoning-insensitive", "SIEVE-<&T1"),
        ("constraint-sensitive", "SIEVE-T3"),
    ]
    rendered = render_report(data)
    assert "SIEVE-&lt;&amp;T1" in rendered
    assert "&lt;original&gt;" in rendered
    assert "&lt;diff&gt;" in rendered
    assert rendered.count("<details>") == 2


def test_report_keeps_raw_perturbed_tests_distinct_from_outcome_stability() -> None:
    stable_broken = ReportEntry(
        ScoreRecord(
            task_id="SIEVE-T1",
            intervention_type="INT-01",
            patch_divergence=0.5,
            outcome_stability=True,
            faithfulness_score=0.5,
        ),
        TestResult(passed=[], failed=["same-baseline-failure"]),
    )
    changed_passing = ReportEntry(
        ScoreRecord(
            task_id="SIEVE-T2",
            intervention_type="INT-02",
            patch_divergence=0.0,
            outcome_stability=False,
            faithfulness_score=0.0,
        ),
        TestResult(passed=["fixed-baseline-failure"], failed=[]),
    )

    rendered = render_report(ReportData((stable_broken, changed_passing)))

    assert "<th>Perturbed tests</th><th>Outcome stability</th>" in rendered
    assert (
        '<td>Tests broke</td><td><span class="badge stable">Stable</span></td>'
        in rendered
    )
    assert (
        '<td>Tests pass</td><td><span class="badge changed">Changed</span></td>'
        in rendered
    )
    assert "<dt>Perturbed tests</dt><dd>Tests broke</dd>" in rendered
    assert '<dt>Outcome stability</dt><dd><span class="badge stable">Stable' in rendered


def test_render_two_by_two_grid_has_exactly_four_labeled_cells_and_counts() -> None:
    grid = render_two_by_two_grid(
        TwoByTwoCounts(
            unchanged_pass=1,
            unchanged_broke=2,
            changed_pass=3,
            changed_broke=4,
        )
    )
    assert grid.count("<article") == 4
    for cell_id, label, count in (
        ("unchanged-pass", "Tests still pass", ">1</strong><span>runs</span>"),
        ("unchanged-broke", "Tests broke", ">2</strong><span>runs</span>"),
        ("changed-pass", "Tests still pass", ">3</strong><span>runs</span>"),
        ("changed-broke", "Tests broke", ">4</strong><span>runs</span>"),
    ):
        assert f'id="{cell_id}"' in grid
        assert label in grid
        assert count in grid


def test_render_report_inserts_grid_before_existing_score_table_and_counts_every_loaded_paired_entry_once(  # noqa: E501
    tmp_path: Path,
) -> None:
    data = load_report_data(_copy_score_runs(tmp_path))
    rendered = render_report(data)
    assert rendered.index('id="two-by-two-grid"') < rendered.index("<table>")
    assert rendered.count('class="outcome-cell ') == 4
    assert ">1</strong><span>runs</span>" in rendered
    assert ">0</strong><span>runs</span>" in rendered
    assert sum(
        (
            summarize_two_by_two(data.entries).unchanged_pass,
            summarize_two_by_two(data.entries).unchanged_broke,
            summarize_two_by_two(data.entries).changed_pass,
            summarize_two_by_two(data.entries).changed_broke,
        )
    ) == len(data.entries)


def test_offline_recorded_score_batch_with_actual_perturbed_test_results_renders_grid_with_counts_equal_to_batch_size(  # noqa: E501
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    _recorded_score_pair(runs, "t1-int01")
    _recorded_score_pair(runs, "t3-int02")
    data = load_report_data(runs)
    counts = summarize_two_by_two(data.entries)
    assert sum(vars(counts).values()) == len(data.entries)
    assert "What changed when the rationale changed?" in render_report(data)


def test_phase4_report_headline_grid_is_legible_and_complete_for_all_four_patch_and_test_outcome_categories() -> (  # noqa: E501
    None
):
    rendered = render_report(_four_category_data())
    for cell_id in (
        "unchanged-pass",
        "unchanged-broke",
        "changed-pass",
        "changed-broke",
    ):
        assert f'id="{cell_id}"' in rendered
        assert ">1</strong><span>runs</span>" in rendered


def test_two_by_two_grid_smoke_one_unchanged_passing_entry_renders_nonblank_cell() -> (
    None
):
    rendered = render_report(ReportData((_entry(0.0, []),)))
    assert 'id="unchanged-pass"' in rendered
    assert ">1</strong><span>runs</span>" in rendered


def test_grid_counts_sum_to_input_count_and_no_entry_appears_in_multiple_bins() -> None:
    entries = _four_category_data().entries
    counts = summarize_two_by_two(entries)
    assert sum(vars(counts).values()) == len(entries)
    assert all(count == 1 for count in vars(counts).values())


def test_two_by_two_grid_markup_matches_committed_golden() -> None:
    actual = _section_markup(render_report(_four_category_data()), "two-by-two-grid")
    expected = _section_markup(
        (REPORT_FIXTURES / "two-by-two-grid.html").read_text(encoding="utf-8"),
        "two-by-two-grid",
    )
    assert actual == expected


def test_static_report_has_four_visible_grid_cells_with_heading_readable_count_text_and_the_exact_tests_pass_or_broke_labels() -> (  # noqa: E501
    None
):
    rendered = render_report(_four_category_data())
    assert ".two-by-two-cells { display: grid;" in rendered
    assert rendered.count('class="outcome-cell ') == 4
    assert "What changed when the rationale changed?" in rendered
    assert "Tests still pass" in rendered
    assert "Tests broke" in rendered


def test_render_honest_limitations_has_semantic_section_heading_ordered_list_and_exact_three_items() -> (  # noqa: E501
    None
):
    rendered = render_honest_limitations()
    assert rendered.startswith(
        '<section id="honest-limitations" aria-labelledby="honest-limitations-heading">'
    )
    assert '<h2 id="honest-limitations-heading">Honest limitations</h2>' in rendered
    assert rendered.count("<li>") == 3
    assert "<em>necessary</em>" in rendered
    assert "<em>to a schema the model was told to fill out</em>" in rendered
    for limitation in HONEST_LIMITATIONS:
        assert limitation in HTMLParserText(rendered).text


def test_honest_limitations_constant_has_exact_spec_order_and_no_empty_item() -> None:
    assert HONEST_LIMITATIONS == (
        (
            "Behavioral insensitivity is evidence the stated reasoning wasn't "
            "necessary for that output — it is not a full mechanistic account of "
            "the model's internal computation."
        ),
        (
            "The structured schema is a deliberate simplification; Sieve audits "
            "faithfulness to a schema the model was told to fill out, not fully "
            "free-form chain-of-thought."
        ),
        (
            "Five tasks is a proof of concept, not a benchmark. The contribution "
            "is the intervention methodology and harness; the task suite is an "
            "illustrative first application."
        ),
    )
    assert all(limitation.strip() for limitation in HONEST_LIMITATIONS)


def test_render_report_includes_limitations_after_grid_and_score_table_for_loaded_score_data(  # noqa: E501
    tmp_path: Path,
) -> None:
    rendered = render_report(load_report_data(_copy_score_runs(tmp_path)))
    assert rendered.index('id="two-by-two-grid"') < rendered.index("<table>")
    assert rendered.index("<table>") < rendered.index('id="honest-limitations"')
    assert rendered.index('id="honest-limitations"') < rendered.index("</main>")


def test_offline_recorded_score_batch_report_contains_limitations_without_live_api_call(  # noqa: E501
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    _recorded_score_pair(runs, "t1-int01")
    rendered = render_report(load_report_data(runs))
    assert (
        _section_markup(rendered, "honest-limitations") == render_honest_limitations()
    )


def test_phase4_generated_report_contains_all_three_verbatim_honest_limitations(
    tmp_path: Path,
) -> None:
    rendered = render_report(load_report_data(_copy_score_runs(tmp_path)))
    text = HTMLParserText(rendered).text
    assert all(limitation in text for limitation in HONEST_LIMITATIONS)


def test_honest_limitations_render_for_single_score_report_is_nonblank() -> None:
    rendered = render_report(ReportData((_entry(0.0, []),)))
    assert _section_markup(rendered, "honest-limitations").strip()


def test_limitations_are_unconditional_unique_and_not_derived_from_score_values() -> (
    None
):
    single_score = render_report(ReportData((_entry(0.0, []),)))
    changed_broken = render_report(ReportData((_entry(1.0, ["vitest"]),)))
    assert _section_markup(single_score, "honest-limitations") == _section_markup(
        changed_broken, "honest-limitations"
    )
    assert len(set(HONEST_LIMITATIONS)) == len(HONEST_LIMITATIONS)


def test_honest_limitations_section_matches_committed_html_golden() -> None:
    actual = render_honest_limitations()
    expected = (
        (REPORT_FIXTURES / "honest-limitations.html")
        .read_text(encoding="utf-8")
        .rstrip("\n")
    )
    assert actual == expected


def test_rendered_report_exposes_visible_honest_limitations_heading_and_three_readable_list_items() -> (  # noqa: E501
    None
):
    parser = _LimitationsParser()
    parser.feed(render_report(ReportData((_entry(0.0, []),))))
    parser.close()
    assert parser.heading == "Honest limitations"
    assert parser.items == list(HONEST_LIMITATIONS)


class HTMLParserText(HTMLParser):
    """Collect text content from a static report without a browser dependency."""

    def __init__(self, document: str) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.feed(document)
        self.close()

    @property
    def text(self) -> str:
        return "".join(self.parts)

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class _LimitationsParser(HTMLParser):
    """Extract the visible limitations heading and list item text."""

    def __init__(self) -> None:
        super().__init__()
        self._inside_limitations = False
        self._inside_heading = False
        self._inside_item = False
        self.heading = ""
        self.items: list[str] = []
        self._item_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "section" and attributes.get("id") == "honest-limitations":
            self._inside_limitations = True
        elif self._inside_limitations and tag == "h2":
            self._inside_heading = True
        elif self._inside_limitations and tag == "li":
            self._inside_item = True
            self._item_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self._inside_heading = False
        elif tag == "li" and self._inside_item:
            self.items.append("".join(self._item_parts))
            self._inside_item = False
        elif tag == "section" and self._inside_limitations:
            self._inside_limitations = False

    def handle_data(self, data: str) -> None:
        if self._inside_heading:
            self.heading += data
        if self._inside_item:
            self._item_parts.append(data)
