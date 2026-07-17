"""Static HTML reporting over persisted Layer 3 score artifacts."""

from __future__ import annotations

import html
import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from pydantic import ValidationError

from sieve.schemas import ScoreRecord, TestResult, TraceRecord


@dataclass(frozen=True)
class ReportEntry:
    """One validated score record and its perturbed trace result."""

    score: ScoreRecord
    perturbed_test_result: TestResult


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
            (
                '<section id="honest-limitations" '
                'aria-labelledby="honest-limitations-heading">'
            ),
            '  <h2 id="honest-limitations-heading">Honest Limitations</h2>',
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


def render_two_by_two_grid(counts: TwoByTwoCounts) -> str:
    """Render the accessible, static, four-cell §7.3 headline grid."""
    cells = (
        (
            "unchanged-pass",
            "Patch unchanged",
            "Tests still pass",
            counts.unchanged_pass,
        ),
        ("unchanged-broke", "Patch unchanged", "Tests broke", counts.unchanged_broke),
        ("changed-pass", "Patch changed", "Tests still pass", counts.changed_pass),
        ("changed-broke", "Patch changed", "Tests broke", counts.changed_broke),
    )
    rendered_cells = "\n".join(
        (
            f'    <article id="{cell_id}"><h3>{patch_label}</h3>'
            f"<p>{test_label}</p><p><strong>{count}</strong> runs</p></article>"
        )
        for cell_id, patch_label, test_label, count in cells
    )
    return "\n".join(
        (
            '<section id="two-by-two-grid" aria-labelledby="two-by-two-heading">',
            '  <h2 id="two-by-two-heading">Causal audit outcomes</h2>',
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
            ReportEntry(score=score, perturbed_test_result=trace.test_result)
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
    grid = render_two_by_two_grid(summarize_two_by_two(data.entries))
    limitations = render_honest_limitations()
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            "  <title>Sieve faithfulness report</title>",
            "  <style>",
            "    #two-by-two-grid { margin: 1.5rem 0; }",
            "    .two-by-two-cells { display: grid; grid-template-columns: "
            "repeat(2, minmax(12rem, 1fr)); gap: 0.75rem; }",
            "    .two-by-two-cells article { border: 1px solid #333; "
            "padding: 0.75rem; }",
            "    .two-by-two-cells h3, .two-by-two-cells p { margin: 0.25rem 0; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <main>",
            "  <h1>Sieve faithfulness report</h1>",
            grid,
            "  <table>",
            "    <thead><tr><th>Task</th><th>Intervention</th>"
            "<th>Patch divergence</th><th>Outcome stability</th>"
            "<th>Faithfulness score</th></tr></thead>",
            "    <tbody>",
            rows,
            "    </tbody>",
            "  </table>",
            limitations,
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


def _render_row(entry: ReportEntry) -> str:
    score = entry.score
    stability = "stable" if score.outcome_stability else "changed"
    return (
        f'      <tr id="{_report_row_id(score)}">'
        f"<td>{html.escape(score.task_id)}</td>"
        f"<td>{html.escape(score.intervention_type)}</td>"
        f"<td>{score.patch_divergence:.3f}</td>"
        f"<td>{stability}</td>"
        f"<td>{score.faithfulness_score:.3f}</td>"
        "</tr>"
    )


def _report_row_id(score: ScoreRecord) -> str:
    """Return a stable, fragment-safe anchor for one score-table row."""
    task_id = quote(score.task_id, safe="")
    intervention_type = quote(score.intervention_type, safe="")
    return f"score-{task_id}-{intervention_type}"
