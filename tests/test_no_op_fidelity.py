"""Phase 1 acceptance and golden regression proof for no-op replay."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

import sieve.cli as cli
from sieve.agent import RecordedBackend
from sieve.resume import ResumeRunner
from sieve.runner import TaskRunner
from sieve.schemas import InterventionMetadata, TraceRecord

REPOSITORY = Path.cwd()
FROZEN_TRACE_PATH = REPOSITORY / "tests/fixtures/phase1/SIEVE-T1-baseline-trace.json"


@pytest.fixture
def frozen_baseline() -> TraceRecord:
    """Load the recorded Phase 0 SIEVE-T1 baseline provenance fixture."""
    return TraceRecord.model_validate_json(
        FROZEN_TRACE_PATH.read_text(encoding="utf-8")
    )


@pytest.fixture
def successful_vitest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep production runner execution deterministic and offline in CI."""

    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", run)


def _resume_backend() -> RecordedBackend:
    return RecordedBackend.from_file_from_step(
        REPOSITORY / "tasks/SIEVE-T1/recorded_resume_run.json", "TSIEVE-T1-S002"
    )


def _complete_no_op_replay(
    tmp_path: Path,
) -> tuple[Path, TraceRecord, Path, TraceRecord]:
    """Create a baseline through TaskRunner, then replay its S002 suffix."""
    baseline_dir, baseline = TaskRunner(REPOSITORY, tmp_path / "baseline-runs").run(
        "SIEVE-T1",
        RecordedBackend.from_file(REPOSITORY / "tasks/SIEVE-T1/recorded_run.json"),
    )
    resumed_dir, resumed = ResumeRunner(REPOSITORY, tmp_path / "resumed-runs").resume(
        baseline, baseline_dir, "TSIEVE-T1-S002", _resume_backend()
    )
    return baseline_dir, baseline, resumed_dir, resumed


def test_frozen_phase1_baseline_trace_validates_as_trace_record(
    frozen_baseline: TraceRecord,
) -> None:
    """Unit: the golden trace is a valid unedited §5.2 baseline."""
    assert any(step.step_id == "TSIEVE-T1-S002" for step in frozen_baseline.steps)
    assert frozen_baseline.run_type == "baseline"
    assert frozen_baseline.intervention == InterventionMetadata()


def test_no_op_fidelity_uses_production_runner_and_resume_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, successful_vitest: None
) -> None:
    """Integration: retain production boundaries, checkpoint, and recorded suffix."""
    del successful_vitest
    run_calls: list[str] = []
    resume_calls: list[tuple[Path, str, RecordedBackend]] = []
    production_run = TaskRunner.run
    production_resume = ResumeRunner.resume

    def spy_run(
        runner: TaskRunner, task_id: str, backend: RecordedBackend
    ) -> tuple[Path, TraceRecord]:
        run_calls.append(task_id)
        return production_run(runner, task_id, backend)

    def spy_resume(
        runner: ResumeRunner,
        baseline: TraceRecord,
        baseline_run_dir: Path,
        target_step_id: str,
        backend: RecordedBackend,
    ) -> tuple[Path, TraceRecord]:
        resume_calls.append((baseline_run_dir, target_step_id, backend))
        return production_resume(
            runner, baseline, baseline_run_dir, target_step_id, backend
        )

    monkeypatch.setattr(TaskRunner, "run", spy_run)
    monkeypatch.setattr(ResumeRunner, "resume", spy_resume)
    baseline_dir, _, _, _ = _complete_no_op_replay(tmp_path)
    assert run_calls == ["SIEVE-T1"]
    assert (baseline_dir / "checkpoints/TSIEVE-T1-S001").is_dir()
    assert len(resume_calls) == 1
    assert resume_calls[0][0] == baseline_dir
    assert resume_calls[0][1] == "TSIEVE-T1-S002"
    assert isinstance(resume_calls[0][2], RecordedBackend)


def test_no_op_resume_executes_complete_sieve_t1_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """System: the regenerated S002 test action executes in a complete trace."""
    commands: list[str] = []

    def run(command: str, *args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        commands.append(command)
        return CompletedProcess(command, 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", run)
    _, _, resumed_dir, resumed = _complete_no_op_replay(tmp_path)
    assert commands == ["npm test", "npm test"]
    assert resumed.steps[-1].step_id == "TSIEVE-T1-S002"
    assert resumed.test_result.passed == ["vitest"]
    assert (
        TraceRecord.model_validate_json(
            (resumed_dir / "trace.json").read_text(encoding="utf-8")
        )
        == resumed
    )


def test_phase_1_no_op_resume_from_step_2_reproduces_baseline_final_diff(
    tmp_path: Path, successful_vitest: None, frozen_baseline: TraceRecord
) -> None:
    """Acceptance: the Phase 1 DoD holds with exact diff equality."""
    del successful_vitest
    baseline_dir, baseline, resumed_dir, resumed = _complete_no_op_replay(tmp_path)
    assert (baseline_dir / "checkpoints/TSIEVE-T1-S001").is_dir()
    assert baseline.final_diff == frozen_baseline.final_diff == resumed.final_diff
    assert baseline.run_id != resumed.run_id
    assert resumed.run_type == "baseline"
    assert resumed.intervention == InterventionMetadata()
    assert [step.claim for step in resumed.steps] == [
        step.claim for step in baseline.steps
    ]
    assert [step.constraint for step in resumed.steps] == [
        step.constraint for step in baseline.steps
    ]
    assert [step.hypothesis for step in resumed.steps] == [
        step.hypothesis for step in baseline.steps
    ]
    assert (resumed_dir / "trace.json").is_file()


def test_no_op_fidelity_smoke(tmp_path: Path, successful_vitest: None) -> None:
    """Smoke: a recorded S002 replay writes its trace artifact."""
    del successful_vitest
    _, _, resumed_dir, _ = _complete_no_op_replay(tmp_path)
    assert (resumed_dir / "trace.json").is_file()


def test_no_op_fidelity_has_nonempty_equal_diffs_and_green_recorded_test_result(
    tmp_path: Path, successful_vitest: None
) -> None:
    """Sanity: the equality is meaningful and task verification is green."""
    del successful_vitest
    _, baseline, _, resumed = _complete_no_op_replay(tmp_path)
    assert baseline.final_diff
    assert baseline.final_diff == resumed.final_diff
    assert baseline.test_result.failed == []
    assert resumed.test_result.failed == []


def test_phase1_golden_baseline_diff_remains_equal_after_no_op_replay(
    tmp_path: Path, successful_vitest: None, frozen_baseline: TraceRecord
) -> None:
    """Regression: CI compares the recorded no-op result with frozen provenance."""
    del successful_vitest
    _, baseline, _, resumed = _complete_no_op_replay(tmp_path)
    assert baseline.final_diff == frozen_baseline.final_diff
    assert resumed.final_diff == frozen_baseline.final_diff


def test_cli_no_op_resume_from_step_2_matches_fixture_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    successful_vitest: None,
    frozen_baseline: TraceRecord,
) -> None:
    """End-to-end: the CLI creates then resumes the exact baseline directory."""
    del successful_vitest
    baseline_runs = tmp_path / "baseline-runs"
    monkeypatch.setattr(
        "sys.argv",
        ["sieve", "run", "--task", "SIEVE-T1", "--runs-dir", str(baseline_runs)],
    )
    cli.main()
    baseline_trace_path = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    resumed_runs = tmp_path / "resumed-runs"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "resume",
            "--baseline-run-dir",
            str(baseline_trace_path.parent),
            "--step",
            "TSIEVE-T1-S002",
            "--runs-dir",
            str(resumed_runs),
        ],
    )
    cli.main()
    resumed_trace_path = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    resumed = TraceRecord.model_validate_json(
        resumed_trace_path.read_text(encoding="utf-8")
    )
    assert resumed.final_diff == frozen_baseline.final_diff
