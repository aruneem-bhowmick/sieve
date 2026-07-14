from __future__ import annotations

import shutil
from pathlib import Path
from subprocess import CompletedProcess
from typing import cast

import pytest

from sieve.agent import (
    AgentTurn,
    RecordedBackend,
    ResumableCodingAgentBackend,
    ToolInvocation,
    ToolResult,
)
from sieve.budget import StepBudgetExceeded
from sieve.replay import ReplayContextItem
from sieve.resume import ResumeRunner
from sieve.runner import TaskRunner
from sieve.schemas import (
    InterventionMetadata,
    PlannedAction,
    StructuredReasoningStep,
    TraceRecord,
)


@pytest.fixture
def successful_vitest(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", run)


@pytest.fixture
def recorded_baseline(
    tmp_path: Path, successful_vitest: None
) -> tuple[Path, TraceRecord]:
    root = Path.cwd()
    return TaskRunner(root, tmp_path / "baseline-runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )


def resume_backend() -> RecordedBackend:
    return RecordedBackend.from_file_from_step(
        Path.cwd() / "tasks/SIEVE-T1/recorded_resume_run.json", "TSIEVE-T1-S002"
    )


class CapturingRecordedBackend(RecordedBackend):
    """Recorded backend that exposes the replay context passed by the runner."""

    def __init__(self, turns: list[AgentTurn]) -> None:
        super().__init__(turns)
        self.contexts: list[list[ReplayContextItem]] = []

    def resume_turn(
        self,
        task_prompt: str,
        replay_context: list[ReplayContextItem],
        history: list[ToolResult],
    ) -> AgentTurn | None:
        self.contexts.append(replay_context)
        return self.next_turn(task_prompt, history)


class NonResumableBackend:
    """A deliberately incomplete backend for runtime interface validation."""

    def next_turn(self, task_prompt: str, history: list[object]) -> AgentTurn | None:
        del task_prompt, history
        return None


def test_resume_runner_rejects_target_absent_from_baseline_trace(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    with pytest.raises(ValueError, match="not present"):
        ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
            baseline, baseline_dir, "TSIEVE-T1-S404", resume_backend()
        )


def test_resume_runner_rejects_missing_pre_target_checkpoint(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    shutil.rmtree(baseline_dir / "checkpoints" / "TSIEVE-T1-S001")
    with pytest.raises(FileNotFoundError, match="pre-target checkpoint"):
        ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
            baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
        )


def test_resume_runner_rejects_non_resumable_backend(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    with pytest.raises(TypeError, match="resume_turn"):
        ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
            baseline,
            baseline_dir,
            "TSIEVE-T1-S002",
            cast(ResumableCodingAgentBackend, NonResumableBackend()),
        )


def test_resume_runner_preserves_empty_baseline_intervention_metadata(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    _, resumed = ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )
    assert resumed.run_type == "baseline"
    assert resumed.intervention == InterventionMetadata()


def test_resume_runner_passes_siv_int_001_context_to_resumable_backend(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    source = resume_backend()
    backend = CapturingRecordedBackend(source._turns)
    _, resumed = ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", backend
    )
    assert [step.step_id for step in resumed.steps] == [
        "TSIEVE-T1-S001",
        "TSIEVE-T1-S002",
    ]
    assert backend.contexts[0][0].step_id == "TSIEVE-T1-S001"


def test_resume_runner_persists_trace_through_canonical_persistence(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    run_dir, resumed = ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )
    saved = TraceRecord.model_validate_json(
        (run_dir / "trace.json").read_text(encoding="utf-8")
    )
    assert saved == resumed


def test_resume_sieve_t1_from_step_2_generates_complete_trace(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    run_dir, resumed = ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )
    assert baseline_dir != run_dir
    assert [step.step_id for step in resumed.steps] == [
        "TSIEVE-T1-S001",
        "TSIEVE-T1-S002",
    ]
    assert resumed.final_diff == baseline.final_diff


def test_resume_runner_smoke_recorded_sieve_t1(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    run_dir, _ = ResumeRunner(Path.cwd(), tmp_path / "resumed", 2).resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )
    assert (run_dir / "trace.json").is_file()


def test_resume_generated_step_ids_are_monotonic_and_task_owned(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    _, resumed = ResumeRunner(Path.cwd(), tmp_path / "resumed").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )
    assert all(step.step_id.startswith("TSIEVE-T1-S") for step in resumed.steps)
    assert resumed.steps == sorted(resumed.steps, key=lambda step: step.step_id)


def test_recorded_resume_fixture_is_deterministic(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    first = ResumeRunner(Path.cwd(), tmp_path / "one").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )[1]
    second = ResumeRunner(Path.cwd(), tmp_path / "two").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", resume_backend()
    )[1]
    assert first.final_diff == second.final_diff


def test_resume_runner_enforces_budget(
    tmp_path: Path, recorded_baseline: tuple[Path, TraceRecord]
) -> None:
    baseline_dir, baseline = recorded_baseline
    first = resume_backend().next_turn("task", [])
    assert first is not None
    second = AgentTurn(
        step=StructuredReasoningStep(
            step_id="TSIEVE-T1-S003",
            claim="A second verification is needed.",
            constraint="Keep the fixture behavior unchanged.",
            hypothesis="The implementation remains null safe.",
            planned_action=PlannedAction.READ_FILE,
            action_target="task.md",
            success_criterion="The task instructions remain available.",
        ),
        action=ToolInvocation(name=PlannedAction.READ_FILE, target="task.md"),
    )
    backend = RecordedBackend([first, second])
    with pytest.raises(StepBudgetExceeded):
        ResumeRunner(Path.cwd(), tmp_path / "resumed", 1).resume(
            baseline, baseline_dir, "TSIEVE-T1-S002", backend
        )
