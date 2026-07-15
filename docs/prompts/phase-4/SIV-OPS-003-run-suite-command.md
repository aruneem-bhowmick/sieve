# SIV-OPS-003 — `sieve run-suite` orchestration command

Read `_PREAMBLE.md` first; it is binding for this implementation prompt.

## Traceability

- Phase: 4 — Full Suite & Report (SIEVE-SPEC.md §13)
- Requirement: `sieve run-suite` orchestration command: runs full suite in one invocation
- Wave: 4
- Depends on: SIV-INT-007, SIV-TSK-002, SIV-RPT-001, SIV-RPT-002, SIV-RPT-003
- Unblocks: none
- Advances DoD: produces all 5 baselines, 15 perturbed runs, 15 score records, and the final rendered report in one invocation.

## Objective

Implement the user-facing Phase 4 orchestration command. It runs each of the five fixtures once for a baseline, applies each INT-01/INT-02/INT-03 intervention to that baseline, scores all 15 pairs, asserts the completed score matrix is non-degenerate, and writes the judge-facing report. The default path must be deterministic and offline; a manual live mode may use the existing direct API backend but is never part of CI.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test taxonomy without restating them.
- Read and persist `TraceRecord` as `runs/<run_id>/trace.json` and `ScoreRecord` as `runs/<perturbed_run_id>/score.json`; write the report to the exact `--report-path` and do not put it in an individual run directory.
- SIV-INT-007 supplies all three interventions, SIV-TSK-002 supplies deterministic recordings for T2/T4/T5, and SIV-RPT-001 through SIV-RPT-003 provide the final report writer. Do not reimplement any of their logic.
- Risk §15: live API nondeterminism breaks CI. Default mode must use `RecordedBackend`; the `--live` branch is covered only by mocks in CI and a manual documented smoke test.

## Interface specification

```python
# src/sieve/suite.py
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sieve.schemas import TraceRecord

TASK_IDS: tuple[str, str, str, str, str] = ("SIEVE-T1", "SIEVE-T2", "SIEVE-T3", "SIEVE-T4", "SIEVE-T5")
INTERVENTION_TYPES: tuple[str, str, str] = ("INT-01", "INT-02", "INT-03")

def target_step_id_for(baseline: TraceRecord) -> str: raise NotImplementedError

@dataclass(frozen=True)
class SuiteResult:
    baseline_run_ids: Sequence[UUID]
    perturbed_run_ids: Sequence[UUID]
    score_paths: Sequence[Path]
    report_path: Path

def run_suite(repo_root: Path, runs_dir: Path, report_path: Path, live: bool = False, model: str = "gpt-5.6", short: bool = False) -> SuiteResult: raise NotImplementedError
```

`target_step_id_for()` must return `baseline.steps[0].step_id`; it must reject an empty baseline and a first ID that does not end in `-S001`. Run every INT-01, INT-02, and INT-03 for a task at that exact ID. The target must be present in the task's INT-02 constraint mapping and INT-03 hypothesis mapping before calling the corresponding intervention; surface a clear task/intervention-specific error if it is not. Add `sieve run-suite` to `build_parser()` with `--runs-dir` defaulting to `runs`, `--report-path` defaulting to `report.html`, `--live`, `--model` defaulting to `gpt-5.6`, and `--short`. Full mode runs the exact `TASK_IDS × INTERVENTION_TYPES` matrix. Short mode runs `SIEVE-T1 × INT-01` only, writes one baseline, one perturbed trace, one score, and a valid report, and prints `report=<absolute path>`. Full mode prints `baselines=5`, `perturbed=15`, `scores=15`, and `report=<absolute path>` on separate lines. Reject pre-existing output directories that would overwrite a run, missing required task recordings, a missing selected intervention fixture or selected target alternative, an empty or non-`S001` baseline, an incomplete full matrix, duplicate matrix keys, or a degenerate completed full score batch.

## Files to create or modify (this section is load-bearing for concurrency — see below)

- **Reads:** `SIEVE-SPEC.md` — Phase 4 DoD, §5 persistence contracts, §8 CI posture, §10, and §11 demo narrative.
- **Reads:** `src/sieve/cli.py` — existing command parsing and backend selection conventions.
- **Reads:** `src/sieve/runner.py`, `src/sieve/interventions.py`, and `src/sieve/scoring.py` — existing production pipeline interfaces.
- **Reads:** `src/sieve/reporting.py` — final static report writer.
- **Reads:** `tasks/SIEVE-T1/`, `tasks/SIEVE-T2/`, `tasks/SIEVE-T3/`, `tasks/SIEVE-T4/`, and `tasks/SIEVE-T5/` — complete recorded task inputs and reviewed intervention files.
- **Writes (creates or modifies):** `src/sieve/suite.py` — matrix planning, recorded/live backend construction, orchestration, completeness validation, and result model.
- **Writes (creates or modifies):** `src/sieve/cli.py` — `run-suite` parser branch and exact summary output.
- **Writes (creates or modifies):** `tests/test_suite.py` — unit, offline integration, matrix, error, smoke, regression, and acceptance tests.
- **Writes (creates or modifies):** `tests/test_cli.py` — `run-suite` parsing, summary output, and mocked live-backend selection tests.
- **Writes (creates or modifies):** `tests/fixtures/phase4/suite/expected-matrix.json` — exact 15 `(task_id, intervention_type)` keys.
- **Writes (creates or modifies):** `tests/fixtures/phase4/suite/expected-report-markers.json` — required grid, table, limitation, and demo-data markers.

## Implementation notes

The full DoD requires “All 5 tasks × 3 interventions (15 perturbed runs + 5 baselines) complete, `report.html` renders correctly, demo narrative (§11) is fully supported by real data, Honest Limitations section is present in the rendered report.” A baseline is run once per task and reused only for that task’s three interventions. Immediately after the baseline, call `target_step_id_for(baseline)` once and use the returned first-step ID for all three task interventions. Score each perturbed run against its paired baseline with `ScoreRunner`; do not score baselines against one another.

The report data must contain exactly 15 unique `(task_id, intervention_type)` score rows. Before writing the full report, require at least one faithful example (`patch_divergence > 0.0` and `outcome_stability is False`) and one unfaithful example (`patch_divergence == 0.0` and `outcome_stability is True`); if the fixed recordings cannot satisfy those two demo assertions, raise a clear error identifying the absent category rather than inventing data. Then call the existing non-degeneracy check. The report must contain the §11 grid, all 15 table rows, and all three limitations. Do not implement §7.4 tool-path divergence.

Live mode must select `OpenAIResponsesBackend` only through existing interfaces and never be run by the automated suite. No API key, model output, raw tool result, or free-form trace text belongs in `SuiteResult` or CLI output.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_full_matrix_contains_exactly_five_tasks_three_interventions_and_unique_keys`; `test_short_matrix_contains_only_t1_int01`; `test_target_step_id_for_returns_first_s001_and_rejects_empty_or_non_s001_baselines`; `test_suite_rejects_missing_recording_missing_target_alternative_duplicate_key_incomplete_matrix_and_missing_demo_category`. |
| Integration | `test_run_suite_connects_runner_intervention_scorer_and_report_writer_for_recorded_short_mode`; `test_full_recorded_suite_writes_one_score_per_perturbed_run` verifies Layer 1→2→3 artifact handoffs. |
| System | `test_full_recorded_five_task_three_intervention_pipeline_produces_five_baselines_fifteen_perturbed_traces_fifteen_scores_and_report` runs the whole recorded pipeline with `RecordedBackend` and the real copied-workspace `npm test` subprocess for every task; do not monkeypatch or mock any runner, intervention, scorer, report writer, or fixture subprocess, and make no live API call. |
| Acceptance | `test_phase4_dod_full_run_suite_report_has_complete_matrix_grid_table_demo_categories_and_honest_limitations` verifies every Phase 4 DoD clause against output data. |
| Smoke | `test_cli_run_suite_short_exits_zero_writes_one_score_and_nonblank_report` is the fast iteration path. |
| Sanity | `test_full_suite_scores_are_in_range_nondegenerate_and_include_faithful_and_unfaithful_demo_categories` checks the real recorded data used for the demo. |
| Regression | `test_recorded_full_suite_matrix_and_report_markers_match_committed_fixtures` compares exact matrix keys and required report markers without a live call. |
| End-to-end | `test_cli_run_suite_full_writes_runs_directory_and_report_html_then_prints_exact_counts_and_absolute_report_path` executes the public command from parser to artifact. |
| API | `test_cli_run_suite_live_selects_openai_backend_with_mocked_backend_only` verifies request path selection without a network call; a manual `sieve run-suite --live` smoke test is documented and never CI-gated. |
| UI | `test_full_run_suite_report_has_visible_two_by_two_grid_fifteen_table_rows_and_honest_limitations_section` parses and renders the static HTML artifact. |

## Definition of done for this prompt

- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via `python -m pytest -v tests/test_suite.py tests/test_cli.py tests/test_reporting.py`.
- [ ] `python -m mypy --strict .`, `python -m ruff check .`, and `python -m black --check .` pass on all new and modified files.
- [ ] No data contract in §5 was altered; all traces and scores retain their canonical `runs/<run_id>/` JSON layout.
- [ ] Golden/regression fixtures, if authored, are committed with the code they characterize.
