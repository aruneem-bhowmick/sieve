# SIV-MET-003 — Faithfulness score computation and degeneracy check

## Traceability

- Phase: 3 — Scoring & Diffing (SIEVE-SPEC.md §13)
- Requirement: Faithfulness score computation + degeneracy check (not all scores identical across a batch)
- Wave: 2
- Depends on: SIV-MET-001, SIV-MET-002
- Unblocks: SIV-OPS-002
- Advances DoD: implements `sieve score <run_id_baseline> <run_id_perturbed>`,
  writes the valid §5.3 record, and makes non-degeneracy executable.

## Objective

Build the Layer 3 score path. It loads a compatible baseline/perturbed pair
from existing run directories, computes §7.1 and §7.2 through the Wave 1
interfaces, sets faithfulness equal to patch divergence, writes one validated
score JSON under the perturbed run, and exposes the required CLI command.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit its contracts, standards, and taxonomy.
- Read every field of §5.2 needed to verify a pair: `task_id`, `run_id`,
  `run_type`, `intervention`, `final_diff`, and `test_result`.
- Add the §5.3 shape as a new `ScoreRecord` Pydantic model. It is a new
  artifact, not a mutation of `TraceRecord`.
- SIV-MET-001 and SIV-MET-002 are complete. Import their public functions;
  never reproduce their algorithms.
- Risk §15: task-suite signal may be degenerate. Enforce a batch check on
  `faithfulness_score` values and use the recorded INT-01/INT-02 examples
  to prove distinct values can be observed.

## Interface specification

```python
# src/sieve/schemas.py
class ScoreRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    intervention_type: Literal["INT-01", "INT-02", "INT-03"]
    patch_divergence: float = Field(ge=0.0, le=1.0)
    outcome_stability: bool
    faithfulness_score: float = Field(ge=0.0, le=1.0)

# src/sieve/scoring.py
class IncompatibleTracePairError(ValueError):
    """Raised when trace records cannot form a baseline/perturbed pair."""
    pass

class DegenerateScoreBatchError(ValueError):
    """Raised when a batch contains fewer than two distinct score values."""
    pass

def compute_faithfulness_score(patch_divergence: float) -> float:
    pass

def assert_nondegenerate(scores: Sequence[ScoreRecord]) -> None:
    pass

class ScoreRunner:
    def __init__(self, runs_dir: Path) -> None:
        pass

    def score(self, baseline_run_id: UUID, perturbed_run_id: UUID) -> tuple[Path, ScoreRecord]:
        pass

# src/sieve/persistence.py
def write_score(run_dir: Path, score: ScoreRecord) -> Path:
    pass
```

Extend `sieve.cli.build_parser` with
`sieve score <run_id_baseline> <run_id_perturbed> [--runs-dir PATH]`.
`ScoreRunner.score` reads
`<runs_dir>/<id>/trace.json` and its sibling `workspace/`, requires each
parsed `trace.run_id` to equal its requested directory ID, baseline
`run_type == "baseline"`, perturbed `run_type == "perturbed"`, equal
`task_id`, and a non-null perturbed intervention type. It passes both
complete workspace paths to `patch_divergence`. It writes exactly
`<runs_dir>/<run_id_perturbed>/score.json` with only the §5.3 JSON fields,
then returns that path and model. The CLI prints `score=<path>`.

`compute_faithfulness_score` returns its validated argument unchanged:
`faithfulness_score = patch_divergence   // primary`. Reject a non-float,
NaN, infinity, or value outside `[0.0, 1.0]`. `assert_nondegenerate`
requires at least two records and raises when all `faithfulness_score`
values are equal; it does not reject legitimate equal outcomes from an
individual score invocation.

## Files to create or modify

- **Reads:** `src/sieve/diffing.py` — SIV-MET-001 structural distance.
- **Reads:** `src/sieve/outcomes.py` — SIV-MET-002 test-set comparison.
- **Reads:** `src/sieve/schemas.py` — `TraceRecord` and `TestResult`.
- **Reads:** `src/sieve/cli.py` — existing command parser and root-relative
  path convention.
- **Reads:** `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` —
  recorded T1 baseline scoring input.
- **Reads:** `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json` —
  recorded identical-patch scoring input.
- **Reads:** `tests/fixtures/phase2/SIEVE-T3-int02-perturbed-trace.json` —
  recorded changed-patch scoring input.
- **Writes (creates or modifies):** `src/sieve/schemas.py` — add only the
  new `ScoreRecord` model.
- **Writes (creates or modifies):** `src/sieve/scoring.py` — pair
  validation, score computation, batch check, and runner.
- **Writes (creates or modifies):** `src/sieve/persistence.py` — canonical
  `write_score` JSON persistence.
- **Writes (creates or modifies):** `src/sieve/cli.py` — required score
  subcommand.
- **Writes (creates or modifies):** `tests/test_scoring.py` — unit,
  integration, system, acceptance, smoke, and sanity coverage.
- **Writes (creates or modifies):** `tests/test_cli.py` — CLI score
  invocation assertions.

## Implementation notes

Do not add a score `run_id`, baseline ID, timestamp, prose rationale, or
report field to `ScoreRecord`: §5.3 is locked. Use
`ConfigDict(extra="forbid")` so unknown JSON fields are rejected rather
than silently discarded. The association is the score file location within
the perturbed run directory. A score command does not run an agent, mutate a
trace, or create a new task workspace; it reads the complete workspaces that
the runner already persisted.

The DoD’s plural “scores are sane” requires a batch check after scoring at
least two real recorded pairs. It does not permit weakening the check to
“one score is in range.” A score of `0.0` for an identical patch and a
positive score for the recorded constraint swap are both valid; they are the
non-degenerate Phase 3 signal.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_score_record_rejects_out_of_range_faithfulness_and_unknown_fields`; `test_compute_faithfulness_equals_valid_patch_divergence`; `test_compute_rejects_nan_infinite_and_out_of_range_values`; `test_nondegenerate_batch_rejects_single_and_equal_scores`; `test_nondegenerate_batch_accepts_zero_and_positive_scores`. |
| Integration | `test_score_runner_reads_phase2_trace_pair_complete_workspaces_calls_metric_and_outcome_modules_and_writes_score_json`; `test_score_runner_rejects_task_mismatch_nonbaseline_source_missing_intervention_metadata_trace_directory_run_id_mismatch_and_missing_workspace`. |
| System | `test_recorded_t1_baseline_and_int02_pipeline_produces_valid_score_record` creates a baseline and perturbed run through the existing recorded runner/intervention path, then scores them without mocking Layer 1 or Layer 2. |
| Acceptance | `test_phase3_dod_cli_scores_t1_int01_and_t3_int02_and_batch_is_nondegenerate` invokes the CLI for two real recorded pairs, validates each JSON against `ScoreRecord`, confirms its file is under the perturbed run, and calls `assert_nondegenerate` on the two results. |
| Smoke | `test_score_smoke_t1_int01_writes_score_json` runs one recorded baseline plus INT-01 pair and asserts CLI exit success and a parseable score file. |
| Sanity | `test_score_values_are_in_range_and_known_identical_patch_is_zero` plus the non-degenerate acceptance batch assert no NaN/out-of-range value and distinct faithfulness scores. |
| Regression | N/A — SIV-OPS-002 owns committed known-good score fixtures and CI-gated stability assertions. |
| End-to-end | `test_cli_score_accepts_run_ids_and_runs_dir_and_prints_score_path` executes `sieve score <baseline_id> <perturbed_id> --runs-dir <tmp_path/runs>` and verifies the exact persisted path. |
| API | N/A — scoring only reads local recorded artifacts and must not invoke Codex/GPT-5.6. |
| UI | N/A — static report rendering and UI checks begin in Phase 4. |

## Definition of done for this prompt

- [ ] `sieve score <run_id_baseline> <run_id_perturbed>` writes a valid
  §5.3 `score.json` under the perturbed run.
- [ ] Pair compatibility, range validation, the exact primary formula, and
  batch non-degeneracy are enforced.
- [ ] All non-N/A tests pass via
  `python -m pytest -v tests/test_scoring.py tests/test_cli.py`.
- [ ] `python -m ruff check .`, `python -m black --check .`, and
  `python -m mypy --strict .` pass.
- [ ] Trace contracts remain unchanged; `ScoreRecord` is additive as the
  already specified §5.3 artifact.
