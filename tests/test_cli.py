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
