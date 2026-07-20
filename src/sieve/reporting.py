"""Static HTML reporting over persisted Layer 3 score artifacts."""

# ruff: noqa: E501

from __future__ import annotations

import html
import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from pydantic import ValidationError

from sieve.schemas import InterventionMetadata, ScoreRecord, TestResult, TraceRecord


@dataclass(frozen=True)
class ReportEntry:
    """One validated score record with read-only presentation data from its trace."""

    score: ScoreRecord
    perturbed_test_result: TestResult
    intervention: InterventionMetadata = field(default_factory=InterventionMetadata)
    final_diff: str = ""


@dataclass(frozen=True)
class ReportData:
    """The deterministic, read-only data projection consumed by reports."""

    entries: Sequence[ReportEntry]


class ReportDataError(ValueError):
    """Raised when persisted score and trace artifacts cannot form a report."""


@dataclass(frozen=True)
class TwoByTwoCounts:
    """Counts for the headline patch-and-test-outcome grid."""

    unchanged_pass: int
    unchanged_broke: int
    changed_pass: int
    changed_broke: int


@dataclass(frozen=True)
class RepresentativeEvidence:
    """One deterministic evidence card selected from the persisted audit batch."""

    kind: str
    heading: str
    entry: ReportEntry


HONEST_LIMITATIONS: tuple[str, str, str] = (
    (
        "Behavioral insensitivity is evidence the stated reasoning wasn't necessary "
        "for that output — it is not a full mechanistic account of the model's "
        "internal computation."
    ),
    (
        "The structured schema is a deliberate simplification; Sieve audits "
        "faithfulness to a schema the model was told to fill out, not fully "
        "free-form chain-of-thought."
    ),
    (
        "Five tasks is a proof of concept, not a benchmark. The contribution is "
        "the intervention methodology and harness; the task suite is an "
        "illustrative first application."
    ),
)


def render_honest_limitations() -> str:
    """Render the always-visible, semantic §11 methodological limitations."""
    rendered_items = (
        HONEST_LIMITATIONS[0].replace("necessary", "<em>necessary</em>"),
        HONEST_LIMITATIONS[1].replace(
            "to a schema the model was told to fill out",
            "<em>to a schema the model was told to fill out</em>",
        ),
        HONEST_LIMITATIONS[2],
    )
    items = "\n".join(f"    <li>{item}</li>" for item in rendered_items)
    return "\n".join(
        (
            '<section id="honest-limitations" aria-labelledby="honest-limitations-heading">',
            '  <p class="eyebrow">Read this before interpreting the score</p>',
            '  <h2 id="honest-limitations-heading">Honest limitations</h2>',
            "  <ol>",
            items,
            "  </ol>",
            "</section>",
        )
    )


def summarize_two_by_two(entries: Sequence[ReportEntry]) -> TwoByTwoCounts:
    """Classify every report entry once using the §7.3 grid axes."""
    counts = {
        "unchanged_pass": 0,
        "unchanged_broke": 0,
        "changed_pass": 0,
        "changed_broke": 0,
    }
    for entry in entries:
        divergence = entry.score.patch_divergence
        if not 0.0 <= divergence <= 1.0:
            raise ValueError("patch_divergence must be within [0.0, 1.0]")
        patch_label = "unchanged" if divergence == 0.0 else "changed"
        test_label = "pass" if not entry.perturbed_test_result.failed else "broke"
        counts[f"{patch_label}_{test_label}"] += 1
    return TwoByTwoCounts(**counts)


def select_representative_evidence(
    entries: Sequence[ReportEntry],
) -> tuple[RepresentativeEvidence, ...]:
    """Select the first deterministic examples for the two demo narrative beats."""
    selected: list[RepresentativeEvidence] = []
    for entry in entries:
        if (
            entry.score.patch_divergence == 0.0
            and not entry.perturbed_test_result.failed
        ):
            selected.append(
                RepresentativeEvidence(
                    "reasoning-insensitive", "Reasoning-insensitive outcome", entry
                )
            )
            break
    for entry in entries:
        if entry.score.patch_divergence > 0.0 and entry.perturbed_test_result.failed:
            selected.append(
                RepresentativeEvidence(
                    "constraint-sensitive", "Constraint-sensitive outcome", entry
                )
            )
            break
    return tuple(selected)


def render_two_by_two_grid(counts: TwoByTwoCounts) -> str:
    """Render the accessible, static, four-cell §7.3 headline grid."""
    cells = (
        (
            "unchanged-pass",
            "unchanged-pass",
            "Patch unchanged",
            "Tests still pass",
            "Reasoning-insensitive",
            counts.unchanged_pass,
        ),
        (
            "unchanged-broke",
            "unchanged-broke",
            "Patch unchanged",
            "Tests broke",
            "Unexpected break",
            counts.unchanged_broke,
        ),
        (
            "changed-pass",
            "changed-pass",
            "Patch changed",
            "Tests still pass",
            "Behavior changed",
            counts.changed_pass,
        ),
        (
            "changed-broke",
            "changed-broke",
            "Patch changed",
            "Tests broke",
            "Constraint-sensitive",
            counts.changed_broke,
        ),
    )
    rendered_cells = "\n".join(
        (
            f'    <article id="{cell_id}" class="outcome-cell {cell_class}">'
            f"<p>{patch_label}</p><h3>{test_label}</h3>"
            f'<strong aria-label="{count} runs">{count}</strong><span>runs</span>'
            f"<small>{meaning}</small></article>"
        )
        for cell_id, cell_class, patch_label, test_label, meaning, count in cells
    )
    return "\n".join(
        (
            '<section id="two-by-two-grid" aria-labelledby="two-by-two-heading">',
            '  <div class="section-heading">',
            '    <p class="eyebrow">The headline evidence</p>',
            '    <h2 id="two-by-two-heading">What changed when the rationale changed?</h2>',
            "    <p>Patch divergence is the primary signal; test outcome gives it practical context.</p>",
            "  </div>",
            '  <div class="two-by-two-cells">',
            rendered_cells,
            "  </div>",
            "</section>",
        )
    )


def load_report_data(runs_dir: Path) -> ReportData:
    """Load and validate direct-run score artifacts in deterministic order."""
    entries: list[ReportEntry] = []
    seen_keys: set[tuple[str, str]] = set()
    try:
        score_paths = sorted(runs_dir.rglob("score.json"))
    except OSError as error:
        raise ReportDataError(f"cannot discover score records in {runs_dir}") from error

    for score_path in score_paths:
        run_dir = score_path.parent
        if run_dir.parent != runs_dir:
            continue
        try:
            directory_run_id = UUID(run_dir.name)
        except ValueError as error:
            raise ReportDataError(
                f"score parent is not a run directory: {run_dir}"
            ) from error
        score = _read_score(score_path)
        trace = _read_trace(run_dir / "trace.json")
        if trace.run_id != directory_run_id:
            raise ReportDataError(f"trace run ID differs from its directory: {run_dir}")
        if trace.run_type != "perturbed":
            raise ReportDataError(f"score sibling trace is not perturbed: {run_dir}")
        if trace.task_id != score.task_id:
            raise ReportDataError(f"score and trace task IDs differ: {run_dir}")
        if trace.intervention.type != score.intervention_type:
            raise ReportDataError(f"score and trace interventions differ: {run_dir}")
        key = (score.task_id, score.intervention_type)
        if key in seen_keys:
            raise ReportDataError(f"duplicate task/intervention score record: {key}")
        seen_keys.add(key)
        entries.append(
            ReportEntry(
                score=score,
                perturbed_test_result=trace.test_result,
                intervention=trace.intervention,
                final_diff=trace.final_diff,
            )
        )

    if not entries:
        raise ReportDataError(f"no score records found in direct runs under {runs_dir}")
    return ReportData(
        entries=tuple(
            sorted(
                entries,
                key=lambda entry: (entry.score.task_id, entry.score.intervention_type),
            )
        )
    )


def render_report(data: ReportData) -> str:
    """Render a complete, deterministic, network-free UTF-8 HTML report."""
    rows = "\n".join(_render_row(entry) for entry in data.entries)
    counts = summarize_two_by_two(data.entries)
    evidence = select_representative_evidence(data.entries)
    task_count = len({entry.score.task_id for entry in data.entries})
    intervention_count = len({entry.score.intervention_type for entry in data.entries})
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>Sieve — causal faithfulness audit</title>",
            "  <style>",
            _REPORT_CSS,
            "  </style>",
            "</head>",
            "<body>",
            "  <main>",
            _render_header(),
            _render_hero(task_count, intervention_count, len(data.entries)),
            _render_method(),
            render_two_by_two_grid(counts),
            _render_evidence_summary(counts, len(data.entries)),
            _render_evidence_cards(evidence),
            _render_matrix(rows),
            render_honest_limitations(),
            _render_footer(),
            "  </main>",
            "</body>",
            "</html>",
            "",
        )
    )


def write_report(runs_dir: Path, output_path: Path) -> Path:
    """Atomically write a rendered report to the exact requested path."""
    rendered = render_report(load_report_data(runs_dir))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output_path.parent, delete=False
        ) as temporary_file:
            temporary_file.write(rendered)
            temporary_path = Path(temporary_file.name)
        os.replace(temporary_path, output_path)
    except OSError as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise ReportDataError(f"cannot write report: {output_path}") from error
    return output_path


def _read_score(path: Path) -> ScoreRecord:
    try:
        return ScoreRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ReportDataError(f"invalid score record: {path}") from error


def _read_trace(path: Path) -> TraceRecord:
    try:
        return TraceRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ReportDataError(f"invalid trace record: {path}") from error


def _render_header() -> str:
    return f"""    <header class="brand-header">
      <a class="brand" href="#top" aria-label="Sieve audit report">
        {_embedded_logo()}
        <span>Sieve</span>
      </a>
      <p>Recorded causal audit · offline evidence</p>
    </header>"""


def _embedded_logo() -> str:
    """Inline the repository logo so a report stays standalone at view time."""
    logo_path = Path(__file__).resolve().parents[2] / "assets" / "sieve.svg"
    try:
        logo = logo_path.read_text(encoding="utf-8")
    except OSError:
        return (
            '<svg class="brand-logo" viewBox="0 0 80 64" aria-hidden="true">'
            '<path fill="currentColor" d="M9 7h62v8H9zm8 13h46v8H17zm8 13h30v8H25zm8 13h14v8H33z"/>'
            '<circle cx="40" cy="58" r="4" fill="#8ce4ba"/></svg>'
        )
    return logo.replace("<svg ", '<svg class="brand-logo" aria-hidden="true" ', 1)


def _render_hero(task_count: int, intervention_count: int, run_count: int) -> str:
    return f"""    <section id="top" class="hero" aria-labelledby="hero-heading">
      <p class="eyebrow">Causal faithfulness auditor for coding agents</p>
      <h1 id="hero-heading">Does an agent’s reasoning actually drive its code?</h1>
      <p class="hero-copy">Sieve edits one structured rationale field mid-run, then compares the resulting patch and tests with the original outcome.</p>
      <dl class="scope" aria-label="Audit scope"><div><dt>{task_count}</dt><dd>tasks</dd></div><div><dt>{intervention_count}</dt><dd>intervention types</dd></div><div><dt>{run_count}</dt><dd>counterfactual runs</dd></div></dl>
    </section>"""


def _render_method() -> str:
    return """    <section id="method" aria-labelledby="method-heading">
      <p class="eyebrow">The method</p>
      <h2 id="method-heading">One controlled edit. Observable software evidence.</h2>
      <ol class="method-steps"><li><span>01</span><strong>Capture</strong><p>Record a structured claim, constraint, and hypothesis alongside each action.</p></li><li><span>02</span><strong>Intervene</strong><p>Edit exactly one field, replay the earlier context, and resume the coding run.</p></li><li><span>03</span><strong>Compare</strong><p>Measure patch divergence and whether the task tests remain green.</p></li></ol>
    </section>"""


def _render_evidence_summary(counts: TwoByTwoCounts, total: int) -> str:
    return f"""    <section id="evidence-summary" aria-labelledby="evidence-summary-heading">
      <p class="eyebrow">What the evidence says</p>
      <h2 id="evidence-summary-heading">Sensitivity is the signal—not a claim about hidden reasoning.</h2>
      <div class="summary-copy"><p><strong>{counts.unchanged_pass} of {total}</strong> counterfactual runs kept the patch unchanged and tests passing. For those outcomes, the edited stated rationale was not necessary to produce the working result.</p><p><strong>{counts.changed_pass + counts.changed_broke} of {total}</strong> runs changed the patch after intervention. That is behavioral sensitivity to the intervention; it does not, by itself, identify the model’s internal mechanism.</p></div>
    </section>"""


def _render_evidence_cards(evidence: Sequence[RepresentativeEvidence]) -> str:
    cards = "\n".join(_render_evidence_card(item) for item in evidence)
    if not cards:
        cards = "      <p>No representative counterfactual category is present in this batch.</p>"
    return "\n".join(
        (
            '<section id="representative-evidence" aria-labelledby="representative-evidence-heading">',
            '  <p class="eyebrow">Representative evidence</p>',
            '  <h2 id="representative-evidence-heading">Two recorded counterfactuals</h2>',
            '  <div class="evidence-cards">',
            cards,
            "  </div>",
            "</section>",
        )
    )


def _render_evidence_card(item: RepresentativeEvidence) -> str:
    entry = item.entry
    intervention = entry.intervention
    original = intervention.original_value or "(blank)"
    replacement = intervention.replacement_value or "(blank)"
    test_outcome = _test_outcome(entry)
    diff = html.escape(entry.final_diff or "No final diff was recorded.")
    return f"""    <article class="evidence-card {item.kind}">
      <p class="card-kicker">{html.escape(item.heading)}</p>
      <h3>{html.escape(entry.score.task_id)} · {html.escape(entry.score.intervention_type)}</h3>
      <dl><div><dt>Field edited</dt><dd>{html.escape(intervention.target_field or "unknown")}</dd></div><div><dt>Patch divergence</dt><dd>{entry.score.patch_divergence:.3f}</dd></div><div><dt>Test outcome</dt><dd><span class="badge {_outcome_class(entry)}">{test_outcome}</span></dd></div></dl>
      <p class="swap"><span>Original</span>{html.escape(original)}<span>Replacement</span>{html.escape(replacement)}</p>
      <details><summary>View counterfactual evidence</summary><p>The run resumed after replacing the stated rationale value above. Its observed outcome is shown here; Sieve does not infer a complete internal causal explanation.</p><pre>{diff}</pre></details>
    </article>"""


def _render_matrix(rows: str) -> str:
    return f"""    <section id="result-matrix" aria-labelledby="result-matrix-heading">
      <p class="eyebrow">Complete audit matrix</p>
      <h2 id="result-matrix-heading">Every task × intervention result</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Task</th><th>Intervention</th><th>Patch divergence</th><th>Test outcome</th><th>Faithfulness score</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table></div>
    </section>"""


def _render_footer() -> str:
    return """    <footer><strong>Sieve</strong><span>This page is a self-contained static report generated from persisted recorded traces and scores. It makes no network request at view time.</span></footer>"""


def _test_outcome(entry: ReportEntry) -> str:
    return "Tests broke" if entry.perturbed_test_result.failed else "Tests pass"


def _outcome_class(entry: ReportEntry) -> str:
    return "broke" if entry.perturbed_test_result.failed else "pass"


def _render_row(entry: ReportEntry) -> str:
    score = entry.score
    return (
        f'          <tr id="{_report_row_id(score)}">'
        f"<td>{html.escape(score.task_id)}</td>"
        f"<td>{html.escape(score.intervention_type)}</td>"
        f"<td>{score.patch_divergence:.3f}</td>"
        f'<td><span class="badge {_outcome_class(entry)}">{_test_outcome(entry)}</span></td>'
        f"<td>{score.faithfulness_score:.3f}</td>"
        "</tr>"
    )


def _report_row_id(score: ScoreRecord) -> str:
    """Return a stable, fragment-safe anchor for one score-table row."""
    task_id = quote(score.task_id, safe="")
    intervention_type = quote(score.intervention_type, safe="")
    return f"score-{task_id}-{intervention_type}"


_REPORT_CSS = """    :root { color-scheme: dark; --bg: #080d12; --panel: #101922; --line: #263442; --text: #ecf2f5; --muted: #a6b5c1; --mint: #8ce4ba; --amber: #f3c778; --rose: #f18e93; }
    * { box-sizing: border-box; }
    body { margin: 0; background: radial-gradient(circle at 80% 0%, #152836 0, var(--bg) 34rem); color: var(--text); font: 16px/1.55 Inter, ui-sans-serif, system-ui, sans-serif; }
    main { width: min(1120px, calc(100% - 2rem)); margin: auto; }
    section { padding: 4.5rem 0; border-bottom: 1px solid var(--line); }
    h1, h2, h3, p { margin-top: 0; } h1, h2, h3 { line-height: 1.05; letter-spacing: -.035em; } h2 { max-width: 720px; font-size: clamp(1.8rem, 4vw, 3rem); } h3 { font-size: 1.1rem; } .eyebrow, .card-kicker { color: var(--mint); font-size: .76rem; font-weight: 760; letter-spacing: .13em; text-transform: uppercase; }
    .brand-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 0; border-bottom: 1px solid var(--line); color: var(--muted); font-size: .82rem; } .brand-header p { margin: 0; } .brand { display: inline-flex; align-items: center; gap: .55rem; color: var(--text); font-size: 1.05rem; font-weight: 780; text-decoration: none; } .brand-logo { width: 42px; height: 34px; color: var(--mint); }
    .hero { padding: clamp(4rem, 11vw, 8.5rem) 0 4rem; } .hero h1 { max-width: 900px; margin-bottom: 1.2rem; font-size: clamp(3.1rem, 8vw, 6.4rem); } .hero-copy { max-width: 650px; color: var(--muted); font-size: 1.18rem; } .scope { display: flex; gap: 3rem; margin: 3rem 0 0; } .scope div { min-width: 9rem; } .scope dt { color: var(--mint); font-size: 2.25rem; font-weight: 800; line-height: 1; } .scope dd { margin: .35rem 0 0; color: var(--muted); }
    .method-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; margin: 2rem 0 0; padding: 1px; background: var(--line); list-style: none; } .method-steps li { padding: 1.5rem; background: var(--panel); } .method-steps span { display: block; margin-bottom: 1.25rem; color: var(--mint); font-size: .8rem; font-weight: 800; } .method-steps strong { display: block; font-size: 1.25rem; } .method-steps p { margin: .35rem 0 0; color: var(--muted); }
    .section-heading > p:last-child, .summary-copy { color: var(--muted); } .two-by-two-cells { display: grid; grid-template-columns: repeat(2, 1fr); gap: .75rem; margin-top: 1.75rem; } .outcome-cell { min-height: 190px; padding: 1.35rem; border: 1px solid var(--line); background: var(--panel); } .outcome-cell > p { margin-bottom: .45rem; color: var(--muted); font-size: .85rem; } .outcome-cell h3 { margin-bottom: 1.3rem; } .outcome-cell strong { display: inline-block; margin-right: .3rem; font-size: 3rem; line-height: 1; } .outcome-cell span { color: var(--muted); } .outcome-cell small { display: block; margin-top: 1rem; color: var(--mint); } .unchanged-broke small, .changed-broke small { color: var(--rose); } .changed-pass small { color: var(--amber); }
    .summary-copy { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2rem; max-width: 900px; } .summary-copy strong { color: var(--text); }
    .evidence-cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; } .evidence-card { padding: 1.5rem; border: 1px solid var(--line); background: var(--panel); } .evidence-card.reasoning-insensitive { border-top: 3px solid var(--mint); } .evidence-card.constraint-sensitive { border-top: 3px solid var(--rose); } .evidence-card dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; } .evidence-card dt { color: var(--muted); font-size: .75rem; } .evidence-card dd { margin: .2rem 0 0; font-weight: 700; overflow-wrap: anywhere; } .badge { display: inline-block; padding: .18rem .45rem; border-radius: 100px; font-size: .78rem; font-weight: 750; white-space: nowrap; } .badge.pass { background: #173d34; color: var(--mint); } .badge.broke { background: #48262e; color: #ffbdc0; } .swap { display: grid; gap: .25rem; margin: 1.25rem 0; padding: 1rem; border-left: 2px solid var(--line); background: #0a1118; overflow-wrap: anywhere; } .swap span { color: var(--muted); font-size: .72rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; } details { border-top: 1px solid var(--line); padding-top: .9rem; } summary { cursor: pointer; color: var(--mint); font-weight: 700; } pre { max-height: 14rem; overflow: auto; padding: .75rem; background: #070b0f; color: #cedae1; font-size: .75rem; white-space: pre-wrap; }
    .table-wrap { overflow-x: auto; border: 1px solid var(--line); } table { width: 100%; border-collapse: collapse; min-width: 650px; } th, td { padding: .9rem 1rem; border-bottom: 1px solid var(--line); text-align: left; } th { color: var(--muted); font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; } tbody tr:last-child td { border-bottom: 0; }
    #honest-limitations { margin: 4.5rem 0; padding: 1.5rem; border: 1px solid #795f35; background: #251d12; } #honest-limitations h2 { margin-bottom: 1rem; } #honest-limitations ol { max-width: 900px; margin: 0; padding-left: 1.25rem; } #honest-limitations li + li { margin-top: .7rem; }
    footer { display: flex; gap: 1rem; justify-content: space-between; padding: 2rem 0 3rem; color: var(--muted); font-size: .82rem; } footer strong { color: var(--text); } footer span { max-width: 640px; text-align: right; }
    @media (max-width: 680px) { main { width: min(100% - 1.4rem, 1120px); } section { padding: 3rem 0; } .brand-header, footer { align-items: flex-start; flex-direction: column; gap: .6rem; } .scope { gap: 1.25rem; } .scope div { min-width: 0; } .method-steps, .two-by-two-cells, .summary-copy, .evidence-cards { grid-template-columns: 1fr; } .evidence-card dl { grid-template-columns: 1fr 1fr; } footer span { text-align: left; } }
"""
