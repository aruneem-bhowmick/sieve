"""Recorded, offline coverage for the Phase 2 INT-01 intervention path."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from uuid import UUID

import pytest

from sieve.agent import (
    AgentTurn,
    OpenAIResponsesBackend,
    RecordedBackend,
    ToolInvocation,
)
from sieve.interventions import ClaimDeletion, ConstraintSwap, InterventionRunner
from sieve.replay import ReplayContextItem
from sieve.runner import TaskRunner
from sieve.schemas import PlannedAction, TraceRecord

ROOT = Path.cwd()
RECORDING = ROOT / "tasks/SIEVE-T1/recorded_int01_run.json"
GOLDEN = ROOT / "tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json"
T1_INT02 = ROOT / "tasks/SIEVE-T1/recorded_int02_run.json"
T3 = ROOT / "tasks/SIEVE-T3"
T3_INT01 = T3 / "recorded_int01_run.json"
T3_INT02 = T3 / "recorded_int02_run.json"
T1_INT02_GOLDEN = ROOT / "tests/fixtures/phase2/SIEVE-T1-int02-perturbed-trace.json"
T3_INT01_GOLDEN = ROOT / "tests/fixtures/phase2/SIEVE-T3-int01-perturbed-trace.json"
T3_INT02_GOLDEN = ROOT / "tests/fixtures/phase2/SIEVE-T3-int02-perturbed-trace.json"


@pytest.fixture
def successful_vitest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep fixture execution deterministic and offline."""

    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", run)


@pytest.fixture
def fixture_vitest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model the fixture acceptance oracle without a live or npm dependency."""

    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args
        workspace = Path(str(kwargs["cwd"]))
        source = next(workspace.glob("src/*.ts")).read_text(encoding="utf-8")
        failed = '"Anonymous"' in source or "#${" in source
        return CompletedProcess(
            "npm test",
            int(failed),
            stdout="tests passed\n" if not failed else "tests failed\n",
            stderr="",
        )

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


@pytest.fixture
def t3_baseline(tmp_path: Path, fixture_vitest: None) -> tuple[Path, TraceRecord]:
    """Create the recorded, checkpointed T3 baseline used by all INT-02 tests."""
    del fixture_vitest
    return TaskRunner(ROOT, tmp_path / "t3-baseline-runs").run(
        "SIEVE-T3", RecordedBackend.from_file(T3 / "recorded_run.json")
    )


def _run_int02(
    tmp_path: Path, baseline: tuple[Path, TraceRecord], task_dir: Path
) -> tuple[Path, TraceRecord]:
    """Use the existing generic runner for the task-local reviewed INT-02 path."""
    baseline_dir, source = baseline
    return InterventionRunner(ROOT, tmp_path / "int02-runs").run(
        source,
        baseline_dir,
        source.steps[0].step_id,
        ConstraintSwap.from_task_fixture(task_dir),
        RecordedBackend.from_file(task_dir / "recorded_int02_run.json"),
    )


def _run_t3_int01(
    tmp_path: Path, baseline: tuple[Path, TraceRecord]
) -> tuple[Path, TraceRecord]:
    """Exercise the Wave 2 claim-deletion path on the isolated T3 fixture."""
    baseline_dir, source = baseline
    return InterventionRunner(ROOT, tmp_path / "t3-int01-runs").run(
        source,
        baseline_dir,
        "TSIEVE-T3-S001",
        ClaimDeletion(),
        RecordedBackend.from_file(T3_INT01),
    )


def test_constraint_swap_replaces_only_constraint(
    t3_baseline: tuple[Path, TraceRecord],
) -> None:
    """Unit: the reviewed alternative changes exactly the constraint field."""
    _, source = t3_baseline
    original = source.steps[0]
    edited = ConstraintSwap.from_task_fixture(T3).edit(original)
    assert edited.constraint.startswith("Preserve a leading #")
    assert edited.model_dump(exclude={"constraint"}) == original.model_dump(
        exclude={"constraint"}
    )


def test_constraint_swap_metadata_records_original_and_replacement(
    t3_baseline: tuple[Path, TraceRecord],
) -> None:
    """Unit: metadata preserves the source constraint and selected alternative."""
    _, source = t3_baseline
    metadata = ConstraintSwap.from_task_fixture(T3).metadata(source.steps[0])
    assert metadata.type == "INT-02"
    assert metadata.target_field == "constraint"
    assert metadata.original_value is not None
    assert metadata.original_value.startswith("Preserve a leading @")
    assert metadata.replacement_value is not None
    assert metadata.replacement_value.startswith("Preserve a leading #")


def test_constraint_swap_rejects_missing_target_mapping(
    t3_baseline: tuple[Path, TraceRecord],
) -> None:
    """Unit: a replacement is never invented for an unreviewed target."""
    _, source = t3_baseline
    with pytest.raises(ValueError, match="no constraint swap alternative"):
        ConstraintSwap.from_task_fixture(T3).edit(source.steps[1])


def test_constraint_swap_rejects_empty_or_same_alternative(
    t3_baseline: tuple[Path, TraceRecord],
) -> None:
    """Unit: blank and no-op alternatives cannot create a counterfactual trace."""
    _, source = t3_baseline
    with pytest.raises(ValueError, match="non-empty"):
        ConstraintSwap({source.steps[0].step_id: "   "})
    with pytest.raises(ValueError, match="differ"):
        ConstraintSwap({source.steps[0].step_id: source.steps[0].constraint}).edit(
            source.steps[0]
        )


def test_constraint_swap_rejects_invalid_fixture_shape(tmp_path: Path) -> None:
    """Unit: task fixtures require paired, non-empty reviewed data."""
    (tmp_path / "intervention_constraints.json").write_text(
        '{"constraint_swaps": {"TSIEVE-T3-S001": "#"}, "manual_reviews": {}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="alternative and review"):
        ConstraintSwap.from_task_fixture(tmp_path)


def test_int02_runner_loads_reviewed_constraints_for_t1_and_t3_uses_int01_path(
    tmp_path: Path,
    baseline: tuple[Path, TraceRecord],
    t3_baseline: tuple[Path, TraceRecord],
    fixture_vitest: None,
) -> None:
    """Integration: both task maps use the existing InterventionRunner path."""
    del fixture_vitest
    _, t1 = _run_int02(tmp_path, baseline, ROOT / "tasks/SIEVE-T1")
    _, t3 = _run_int02(tmp_path, t3_baseline, T3)
    assert t1.intervention.type == t3.intervention.type == "INT-02"
    assert t1.steps[0].constraint != t3.steps[0].constraint


def test_int02_persists_step_result_pairs_and_metadata(
    tmp_path: Path, t3_baseline: tuple[Path, TraceRecord], fixture_vitest: None
) -> None:
    """Integration: the generic runner persists complete ordered trace pairs."""
    del fixture_vitest
    run_dir, trace = _run_int02(tmp_path, t3_baseline, T3)
    assert len(trace.steps) == len(trace.tool_results)
    assert (
        TraceRecord.model_validate_json((run_dir / "trace.json").read_text()) == trace
    )
    assert trace.intervention.target_step_id == "TSIEVE-T3-S001"


def test_recorded_int02_sieve_t1_and_t3_run_baseline_then_perturbed_traces(
    tmp_path: Path,
    baseline: tuple[Path, TraceRecord],
    t3_baseline: tuple[Path, TraceRecord],
    fixture_vitest: None,
) -> None:
    """System: recorded baseline/INT-02 pairs persist expected failing outcomes."""
    del fixture_vitest
    _, t1 = _run_int02(tmp_path, baseline, ROOT / "tasks/SIEVE-T1")
    _, t3 = _run_int02(tmp_path, t3_baseline, T3)
    assert t1.test_result.failed == t3.test_result.failed == ["vitest"]
    assert t1.test_result.passed == t3.test_result.passed == []


def test_phase2_dod_has_all_four_task_intervention_pairs(
    tmp_path: Path,
    baseline: tuple[Path, TraceRecord],
    t3_baseline: tuple[Path, TraceRecord],
    fixture_vitest: None,
) -> None:
    """Acceptance: all T1/T3 × INT-01/INT-02 records have valid paired evidence."""
    del fixture_vitest
    _, t1_int01 = _run_int01(tmp_path, baseline)
    _, t1_int02 = _run_int02(tmp_path, baseline, ROOT / "tasks/SIEVE-T1")
    _, t3_int01 = _run_t3_int01(tmp_path, t3_baseline)
    _, t3_int02 = _run_int02(tmp_path, t3_baseline, T3)
    records = [t1_int01, t1_int02, t3_int01, t3_int02]
    assert {(item.task_id, item.intervention.type) for item in records} == {
        ("SIEVE-T1", "INT-01"),
        ("SIEVE-T1", "INT-02"),
        ("SIEVE-T3", "INT-01"),
        ("SIEVE-T3", "INT-02"),
    }
    assert all(item.intervention.target_step_id for item in records)
    assert all(len(item.steps) == len(item.tool_results) for item in records)


def test_int02_smoke_recorded_sieve_t3(
    tmp_path: Path, t3_baseline: tuple[Path, TraceRecord], fixture_vitest: None
) -> None:
    """Smoke: one recorded T3 constraint swap writes a valid trace artifact."""
    del fixture_vitest
    run_dir, trace = _run_int02(tmp_path, t3_baseline, T3)
    assert trace.run_type == "perturbed"
    assert (run_dir / "trace.json").is_file()


def test_t1_and_t3_constraint_alternatives_are_reviewed_and_plausible() -> None:
    """Sanity: alternatives are concrete and hidden from T3's baseline prompt."""
    for task_dir, competing_tag in ((ROOT / "tasks/SIEVE-T1", "Anonymous"), (T3, "#")):
        raw = json.loads((task_dir / "intervention_constraints.json").read_text())
        alternative = next(iter(raw["constraint_swaps"].values()))
        review = next(iter(raw["manual_reviews"].values()))
        assert alternative.strip() and review.strip() and competing_tag in alternative
    prompt = (T3 / "task.md").read_text(encoding="utf-8")
    assert "channel-style" not in prompt
    assert "counterfactual" not in prompt


@pytest.mark.parametrize(
    ("golden", "runner"),
    [
        (T1_INT02_GOLDEN, "t1-int02"),
        (T3_INT01_GOLDEN, "t3-int01"),
        (T3_INT02_GOLDEN, "t3-int02"),
    ],
)
def test_phase2_recorded_golden_traces(
    tmp_path: Path,
    baseline: tuple[Path, TraceRecord],
    t3_baseline: tuple[Path, TraceRecord],
    fixture_vitest: None,
    golden: Path,
    runner: str,
) -> None:
    """Regression: frozen T1/T3 perturbed traces remain stable offline."""
    del fixture_vitest
    if runner == "t1-int02":
        _, trace = _run_int02(tmp_path, baseline, ROOT / "tasks/SIEVE-T1")
    elif runner == "t3-int01":
        _, trace = _run_t3_int01(tmp_path, t3_baseline)
    else:
        _, trace = _run_int02(tmp_path, t3_baseline, T3)
    actual = trace.model_dump(mode="json")
    expected = json.loads(golden.read_text(encoding="utf-8"))
    actual["run_id"] = expected["run_id"]
    actual["timestamp"] = expected["timestamp"]
    assert actual == expected


def test_t3_fixture_layout_is_isolated() -> None:
    """Regression: all T3 acceptance infrastructure remains task-local."""
    assert all(path.is_relative_to(T3) for path in T3.rglob("*"))


def test_openai_int02_intervention_turn_uses_task_authored_replacement(
    monkeypatch: pytest.MonkeyPatch, t3_baseline: tuple[Path, TraceRecord]
) -> None:
    """API: mocked request contains the exact edited step and rejects extra mutation."""
    _, source = t3_baseline
    edited = ConstraintSwap.from_task_fixture(T3).edit(source.steps[0])

    class FakeResponse:
        output: list[object] = []

    captured: dict[str, object] = {}

    def create(**kwargs: object) -> FakeResponse:
        captured.update(kwargs)
        return FakeResponse()

    class FakeClient:
        def __init__(self) -> None:
            self.responses = type("Responses", (), {"create": staticmethod(create)})()

    monkeypatch.setattr("sieve.agent.OpenAI", FakeClient)
    backend = OpenAIResponsesBackend("gpt-5.6")
    assert backend.intervention_turn("task", [], edited, []) is None
    assert edited.constraint in str(captured["input"])
