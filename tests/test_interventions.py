"""Recorded, offline coverage for the Phase 2 INT-01 intervention path."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from uuid import UUID

import pytest

from sieve.agent import AgentTurn, RecordedBackend, ToolInvocation
from sieve.interventions import ClaimDeletion, InterventionRunner
from sieve.replay import ReplayContextItem
from sieve.runner import TaskRunner
from sieve.schemas import PlannedAction, TraceRecord

ROOT = Path.cwd()
RECORDING = ROOT / "tasks/SIEVE-T1/recorded_int01_run.json"
GOLDEN = ROOT / "tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json"


@pytest.fixture
def successful_vitest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep fixture execution deterministic and offline."""

    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", run)


@pytest.fixture
def baseline(tmp_path: Path, successful_vitest: None) -> tuple[Path, TraceRecord]:
    """Create the paired, checkpointed recorded SIEVE-T1 baseline."""
    del successful_vitest
    return TaskRunner(ROOT, tmp_path / "baseline-runs").run(
        "SIEVE-T1", RecordedBackend.from_file(ROOT / "tasks/SIEVE-T1/recorded_run.json")
    )


def _run_int01(
    tmp_path: Path, baseline: tuple[Path, TraceRecord], step: str = "TSIEVE-T1-S001"
) -> tuple[Path, TraceRecord]:
    """Run the production INT-01 runner with its frozen backend fixture."""
    baseline_dir, source = baseline
    return InterventionRunner(ROOT, tmp_path / "perturbed-runs").run(
        source,
        baseline_dir,
        step,
        ClaimDeletion(),
        RecordedBackend.from_file(RECORDING),
    )


def _run_int01_at_s002(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> tuple[Path, TraceRecord]:
    """Run the same production path with S001 retained as the fixed prefix."""
    baseline_dir, source = baseline
    edited = ClaimDeletion().edit(source.steps[1])
    backend = RecordedBackend(
        [
            AgentTurn(
                step=edited,
                action=ToolInvocation(name=PlannedAction.RUN_TESTS, target="npm test"),
            )
        ]
    )
    return InterventionRunner(ROOT, tmp_path / "perturbed-s002").run(
        source, baseline_dir, "TSIEVE-T1-S002", ClaimDeletion(), backend
    )


def test_claim_deletion_blanks_only_claim(baseline: tuple[Path, TraceRecord]) -> None:
    """Unit: the exact target step is retained except for the empty claim."""
    _, source = baseline
    original = source.steps[0]
    edited = ClaimDeletion().edit(original)
    assert edited.claim == ""
    assert edited.model_dump(exclude={"claim"}) == original.model_dump(
        exclude={"claim"}
    )


def test_claim_deletion_metadata_records_original_and_empty_replacement(
    baseline: tuple[Path, TraceRecord],
) -> None:
    """Unit: §5.2 metadata proves exactly which field changed."""
    _, source = baseline
    metadata = ClaimDeletion().metadata(source.steps[0])
    assert metadata.type == "INT-01"
    assert metadata.target_step_id == source.steps[0].step_id
    assert metadata.target_field == "claim"
    assert metadata.original_value == source.steps[0].claim
    assert metadata.replacement_value == ""


def test_intervention_runner_rejects_unknown_target(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Unit: unknown target IDs never create a perturbed artifact."""
    baseline_dir, source = baseline
    with pytest.raises(ValueError, match="not present"):
        InterventionRunner(ROOT, tmp_path / "perturbed").run(
            source,
            baseline_dir,
            "TSIEVE-T1-S404",
            ClaimDeletion(),
            RecordedBackend.from_file(RECORDING),
        )


def test_intervention_runner_rejects_nonbaseline_source_trace(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Unit: perturbing a perturbation is intentionally unsupported."""
    baseline_dir, source = baseline
    with pytest.raises(ValueError, match="baseline source"):
        InterventionRunner(ROOT, tmp_path / "perturbed").run(
            source.model_copy(update={"run_type": "perturbed"}),
            baseline_dir,
            "TSIEVE-T1-S001",
            ClaimDeletion(),
            RecordedBackend.from_file(RECORDING),
        )


def test_int01_runner_uses_phase1_prefix_context_and_checkpoint(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Integration: an S002 edit restores S001 and supplies it as fixed context."""
    baseline_dir, source = baseline
    edited = ClaimDeletion().edit(source.steps[1])
    second = AgentTurn(
        step=edited,
        action=ToolInvocation(name=PlannedAction.RUN_TESTS, target="npm test"),
    )

    class CapturingBackend(RecordedBackend):
        def __init__(self) -> None:
            super().__init__([second])
            self.context: list[ReplayContextItem] = []

        def intervention_turn(
            self,
            task_prompt: str,
            replay_context: list[ReplayContextItem],
            edited_step: object,
            history: object,
        ) -> AgentTurn | None:
            del edited_step, history
            self.context = replay_context
            return self.next_turn(task_prompt, [])

    backend = CapturingBackend()
    InterventionRunner(ROOT, tmp_path / "perturbed").run(
        source, baseline_dir, "TSIEVE-T1-S002", ClaimDeletion(), backend
    )
    assert backend.context[0].step_id == "TSIEVE-T1-S001"
    assert (baseline_dir / "checkpoints/TSIEVE-T1-S001").is_dir()


def test_int01_runner_copies_fixed_prefix_tool_result_pairs(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Integration: S002 keeps the paired raw S001 result at index zero."""
    _, source = baseline
    _, perturbed = _run_int01_at_s002(tmp_path, baseline)
    assert perturbed.tool_results[0] == source.tool_results[0]
    assert len(perturbed.steps) == len(perturbed.tool_results) == 2


def test_int01_runner_persists_tool_result_pairs(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Integration: all regenerated actions have one ordered raw result."""
    _, perturbed = _run_int01(tmp_path, baseline)
    assert len(perturbed.steps) == len(perturbed.tool_results)
    assert all(
        step.planned_action == result.name and step.action_target == result.target
        for step, result in zip(perturbed.steps, perturbed.tool_results, strict=True)
    )


def test_intervention_runner_writes_trace_through_canonical_persistence(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Integration: canonical JSON can be read back as a TraceRecord."""
    run_dir, perturbed = _run_int01(tmp_path, baseline)
    assert (
        TraceRecord.model_validate_json(
            (run_dir / "trace.json").read_text(encoding="utf-8")
        )
        == perturbed
    )


def test_recorded_int01_sieve_t1_runs_baseline_then_perturbed_trace(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """System: the actual fixture action executes in a distinct perturbed run."""
    baseline_dir, source = baseline
    perturbed_dir, perturbed = _run_int01(tmp_path, baseline)
    assert baseline_dir != perturbed_dir
    assert len(source.steps) == len(perturbed.steps) == 2
    assert perturbed.steps[0].claim == ""
    assert perturbed.tool_results[1].name == PlannedAction.RUN_TESTS


def test_phase2_int01_sieve_t1_produces_paired_trace_records_with_populated_metadata(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Acceptance: the reusable Phase 2 T1 pair satisfies its DoD slice."""
    _, source = baseline
    _, perturbed = _run_int01(tmp_path, baseline)
    assert source.task_id == perturbed.task_id == "SIEVE-T1"
    assert source.run_id != perturbed.run_id
    assert perturbed.run_type == "perturbed"
    assert perturbed.intervention.type == "INT-01"
    assert perturbed.intervention.target_field == "claim"
    assert len(perturbed.steps) == len(perturbed.tool_results)


def test_int01_smoke_recorded_sieve_t1(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Smoke: a bounded recorded S001 intervention writes its trace artifact."""
    baseline_dir, source = baseline
    run_dir, _ = InterventionRunner(ROOT, tmp_path / "perturbed", 2).run(
        source,
        baseline_dir,
        "TSIEVE-T1-S001",
        ClaimDeletion(),
        RecordedBackend.from_file(RECORDING),
    )
    assert (run_dir / "trace.json").is_file()


def test_int01_edited_trace_has_one_empty_claim_and_no_other_target_field_change(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Sanity: both supported target positions retain complete pair cardinality."""
    _, source = baseline
    _, perturbed = _run_int01(tmp_path, baseline)
    _, perturbed_s002 = _run_int01_at_s002(tmp_path, baseline)
    assert [step.claim for step in perturbed.steps].count("") == 1
    assert perturbed.steps[0].model_dump(exclude={"claim"}) == source.steps[
        0
    ].model_dump(exclude={"claim"})
    assert len(perturbed.steps) == len(perturbed.tool_results) == 2
    assert len(perturbed_s002.steps) == len(perturbed_s002.tool_results) == 2


def test_recorded_int01_sieve_t1_matches_phase2_golden_trace(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Regression: the offline perturbed trace is stable except provenance values."""
    _, perturbed = _run_int01(tmp_path, baseline)
    actual = perturbed.model_dump(mode="json")
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    actual["run_id"] = expected["run_id"]
    actual["timestamp"] = expected["timestamp"]
    assert actual == expected


def test_intervention_runner_rejects_incomplete_fixed_prefix_pairs(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> None:
    """Regression: legacy/incomplete S002 sources cannot emit invalid pairs."""
    baseline_dir, source = baseline
    incomplete = source.model_copy(update={"tool_results": []})
    with pytest.raises(ValueError, match="paired tool_results"):
        InterventionRunner(ROOT, tmp_path / "perturbed").run(
            incomplete,
            baseline_dir,
            "TSIEVE-T1-S002",
            ClaimDeletion(),
            RecordedBackend.from_file(RECORDING),
        )


def test_intervention_golden_uses_valid_uuid_provenance() -> None:
    """Regression fixture itself remains a valid frozen §5.2 document."""
    raw = json.loads(GOLDEN.read_text(encoding="utf-8"))
    UUID(raw["run_id"])
    assert TraceRecord.model_validate(raw).intervention.type == "INT-01"
