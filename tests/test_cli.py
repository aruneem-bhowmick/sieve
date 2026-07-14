from pathlib import Path
from uuid import uuid4

import pytest
from pytest import CaptureFixture, MonkeyPatch

from sieve import cli
from sieve.persistence import create_run_directory, write_trace
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


def test_cli_intervene_int01_creates_perturbed_trace(
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
    perturbed_runs = tmp_path / "perturbed-runs"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "intervene",
            "--baseline-run-dir",
            str(baseline_trace.parent),
            "--step",
            "TSIEVE-T1-S001",
            "--type",
            "INT-01",
            "--runs-dir",
            str(perturbed_runs),
        ],
    )
    cli.main()
    perturbed_trace = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    trace = TraceRecord.model_validate_json(perturbed_trace.read_text(encoding="utf-8"))
    assert trace.run_type == "perturbed"
    assert trace.intervention.type == "INT-01"


def test_cli_int02_loads_task_local_constraint_fixture(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
) -> None:
    """Integration: the CLI loads T3's reviewed fixture before intervention."""
    from subprocess import CompletedProcess

    def fixture_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args
        workspace = Path(str(kwargs["cwd"]))
        failed = "#${" in (workspace / "src/formatUsername.ts").read_text()
        return CompletedProcess(
            "npm test",
            int(failed),
            "tests failed\n" if failed else "tests passed\n",
            "",
        )

    monkeypatch.setattr("sieve.runner.subprocess.run", fixture_vitest)
    baseline_runs = tmp_path / "baseline-runs"
    monkeypatch.setattr(
        "sys.argv",
        ["sieve", "run", "--task", "SIEVE-T3", "--runs-dir", str(baseline_runs)],
    )
    cli.main()
    baseline_trace = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    perturbed_runs = tmp_path / "perturbed-runs"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "intervene",
            "--baseline-run-dir",
            str(baseline_trace.parent),
            "--step",
            "TSIEVE-T3-S001",
            "--type",
            "INT-02",
            "--runs-dir",
            str(perturbed_runs),
        ],
    )
    cli.main()
    perturbed_trace = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    trace = TraceRecord.model_validate_json(perturbed_trace.read_text(encoding="utf-8"))
    assert trace.intervention.replacement_value is not None
    assert trace.intervention.replacement_value.startswith("Preserve a leading #")
    assert len(trace.steps) == len(trace.tool_results)


def test_cli_score_accepts_run_ids_and_runs_dir_and_prints_score_path(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
) -> None:
    baseline_id = uuid4()
    perturbed_id = uuid4()
    runs = tmp_path / "runs"
    baseline_dir = create_run_directory(runs, baseline_id)
    perturbed_dir = create_run_directory(runs, perturbed_id)
    for run_dir in (baseline_dir, perturbed_dir):
        workspace = run_dir / "workspace" / "src"
        workspace.mkdir(parents=True)
        (workspace / "value.ts").write_text(
            "export function value(): number { return 1; }\n", encoding="utf-8"
        )
    diff = (
        "--- a/src/value.ts\n+++ b/src/value.ts\n@@ -1 +1 @@\n"
        "-export function value(): number { return 1; }\n"
        "+export function value(): number { return 1; }\n"
    )
    write_trace(
        baseline_dir,
        TraceRecord(
            task_id="SIEVE-T1",
            run_id=baseline_id,
            run_type="baseline",
            intervention=InterventionMetadata(),
            steps=[],
            final_diff=diff,
            test_result=TestResult(passed=["vitest"], failed=[]),
        ),
    )
    write_trace(
        perturbed_dir,
        TraceRecord(
            task_id="SIEVE-T1",
            run_id=perturbed_id,
            run_type="perturbed",
            intervention=InterventionMetadata(
                type="INT-01",
                target_step_id="TSIEVE-T1-S001",
                target_field="claim",
                original_value="claim",
                replacement_value="",
            ),
            steps=[],
            final_diff=diff,
            test_result=TestResult(passed=["vitest"], failed=[]),
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "score",
            str(baseline_id),
            str(perturbed_id),
            "--runs-dir",
            str(runs),
        ],
    )

    cli.main()

    path = perturbed_dir / "score.json"
    assert capsys.readouterr().out.strip() == f"score={path}"
    assert path.is_file()


def test_cli_rejects_resume_and_intervene_without_required_artifacts(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    for command in ("resume", "intervene"):
        arguments = [
            "sieve",
            command,
            "--baseline-run-dir",
            str(tmp_path / "missing"),
            "--step",
            "TSIEVE-T1-S001",
        ]
        if command == "intervene":
            arguments.extend(["--type", "INT-01"])
        monkeypatch.setattr("sys.argv", arguments)
        with pytest.raises(ValueError, match="baseline run directory"):
            cli.main()


def test_cli_live_paths_select_the_openai_backend_without_a_network_call(
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
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    (baseline_dir / "checkpoints").mkdir()
    write_trace(baseline_dir, trace)
    monkeypatch.setattr("sieve.cli.OpenAIResponsesBackend", lambda model: object())

    def fake_task_run(
        self: object, task_id: str, backend: object
    ) -> tuple[Path, TraceRecord]:
        del self, task_id, backend
        return tmp_path, trace

    def fake_resume(self: object, *args: object) -> tuple[Path, TraceRecord]:
        del self, args
        return tmp_path, trace

    def fake_intervene(self: object, *args: object) -> tuple[Path, TraceRecord]:
        del self, args
        return tmp_path, trace

    monkeypatch.setattr("sieve.cli.TaskRunner.run", fake_task_run)
    monkeypatch.setattr("sieve.cli.ResumeRunner.resume", fake_resume)
    monkeypatch.setattr("sieve.cli.InterventionRunner.run", fake_intervene)
    commands = (
        ["sieve", "run", "--task", "SIEVE-T1", "--live"],
        [
            "sieve",
            "resume",
            "--baseline-run-dir",
            str(baseline_dir),
            "--step",
            "TSIEVE-T1-S001",
            "--live",
        ],
        [
            "sieve",
            "intervene",
            "--baseline-run-dir",
            str(baseline_dir),
            "--step",
            "TSIEVE-T1-S001",
            "--type",
            "INT-01",
            "--live",
        ],
    )
    for command in commands:
        monkeypatch.setattr("sys.argv", command)
        cli.main()

    assert capsys.readouterr().out.count("run_id=") == 3
