from pathlib import Path
from uuid import uuid4

from pytest import CaptureFixture, MonkeyPatch

from sieve import cli
from sieve.schemas import InterventionMetadata, TestResult, TraceRecord


def test_cli_runs_recorded_task_and_prints_trace(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
) -> None:
    trace = TraceRecord(
        task_id="SIEVE-T1",
        run_id=uuid4(),
        run_type="baseline",
        intervention=InterventionMetadata(),
        steps=[],
        final_diff="",
        test_result=TestResult(passed=[], failed=[]),
    )

    def fake_run(
        self: object, task_id: str, backend: object
    ) -> tuple[Path, TraceRecord]:
        del self, task_id, backend
        return tmp_path, trace

    monkeypatch.setattr("sieve.cli.TaskRunner.run", fake_run)
    monkeypatch.setattr("sys.argv", ["sieve", "run", "--task", "SIEVE-T1"])
    cli.main()
    assert f"run_id={trace.run_id}" in capsys.readouterr().out


def test_cli_resume_writes_new_trace_json(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
) -> None:
    from subprocess import CompletedProcess

    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    baseline_runs = tmp_path / "baseline-runs"
    monkeypatch.setattr(
        "sys.argv",
        ["sieve", "run", "--task", "SIEVE-T1", "--runs-dir", str(baseline_runs)],
    )
    cli.main()
    baseline_trace = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    resumed_runs = tmp_path / "resumed-runs"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "resume",
            "--baseline-run-dir",
            str(baseline_trace.parent),
            "--step",
            "TSIEVE-T1-S002",
            "--runs-dir",
            str(resumed_runs),
        ],
    )
    cli.main()
    resumed_trace = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    assert TraceRecord.model_validate_json(resumed_trace.read_text(encoding="utf-8"))
