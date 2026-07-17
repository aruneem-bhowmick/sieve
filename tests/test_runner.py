import json
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

import pytest

from sieve import cli
from sieve.agent import AgentTurn, RecordedBackend, ToolInvocation
from sieve.runner import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    TaskRunner,
    _workspace_path,
    unified_directory_diff,
)
from sieve.schemas import PlannedAction, StructuredReasoningStep, TraceRecord


def test_recorded_t1_run_writes_valid_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    repository = Path.cwd()
    backend = RecordedBackend.from_file(repository / "tasks/SIEVE-T1/recorded_run.json")
    run_dir, trace = TaskRunner(repository, tmp_path / "runs").run("SIEVE-T1", backend)
    saved = json.loads((run_dir / "trace.json").read_text(encoding="utf-8"))
    assert saved["task_id"] == "SIEVE-T1"
    assert trace.test_result.passed == ["vitest"]
    assert len(trace.tool_results) == len(trace.steps) == 2
    assert trace.tool_results[1].name == PlannedAction.RUN_TESTS
    assert trace.tool_results[1].target == "npm test"
    assert "return name?.trim()" in trace.final_diff
    assert (run_dir / "checkpoints" / "initial" / "src" / "normalizeName.ts").is_file()
    checkpoint = run_dir / "checkpoints" / "TSIEVE-T1-S001" / "src" / "normalizeName.ts"
    assert "return name?.trim()" in checkpoint.read_text(encoding="utf-8")


def test_unified_directory_diff_is_empty_for_equal_directories(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "file.ts").write_text("export {};\n", encoding="utf-8")
    (right / "file.ts").write_text("export {};\n", encoding="utf-8")
    assert unified_directory_diff(left, right) == ""


def test_workspace_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="remain inside"):
        _workspace_path(tmp_path, "../outside.txt")


def test_runner_rejects_unknown_fixture(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="unknown task fixture"):
        TaskRunner(Path.cwd(), tmp_path).run("SIEVE-T404", RecordedBackend([]))


def test_runner_enforces_step_budget(tmp_path: Path) -> None:
    step = StructuredReasoningStep(
        step_id="TSIEVE-T1-S001",
        claim="claim",
        constraint="constraint",
        hypothesis="hypothesis",
        planned_action=PlannedAction.READ_FILE,
        action_target="task.md",
        success_criterion="criterion",
    )
    turn = AgentTurn(
        step=step,
        action=ToolInvocation(name=PlannedAction.READ_FILE, target="task.md"),
    )
    with pytest.raises(RuntimeError, match="step budget"):
        TaskRunner(Path.cwd(), tmp_path, max_steps=1).run(
            "SIEVE-T1", RecordedBackend([turn])
        )


def test_runner_command_execution_uses_utf8_with_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args
        captured.update(kwargs)
        return CompletedProcess("npm test", 0, stdout="Vitest ✓\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", run)
    root = Path.cwd()
    _, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )

    assert captured["text"] is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["timeout"] == DEFAULT_COMMAND_TIMEOUT_SECONDS
    assert trace.tool_results[-1].output == "Vitest ✓\n"


def test_runner_records_timed_out_test_command_as_a_failed_test_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args
        captured.update(kwargs)
        raise TimeoutExpired(
            "npm test", DEFAULT_COMMAND_TIMEOUT_SECONDS, "partial stdout\n", b"stderr"
        )

    monkeypatch.setattr("sieve.runner.subprocess.run", run)
    root = Path.cwd()
    _, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )

    result = trace.tool_results[-1]
    assert captured["timeout"] == DEFAULT_COMMAND_TIMEOUT_SECONDS
    assert result.succeeded is False
    assert (
        result.output == "partial stdout\nstderr\n"
        f"command timed out after {DEFAULT_COMMAND_TIMEOUT_SECONDS} seconds\n"
    )
    assert trace.test_result.passed == []
    assert trace.test_result.failed == ["vitest"]


def test_runner_rejects_nonpositive_command_timeout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        TaskRunner(Path.cwd(), tmp_path, command_timeout_seconds=0)


def test_runner_persists_step_result_pairs_through_canonical_write_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    root = Path.cwd()
    run_dir, _ = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )

    saved = json.loads((run_dir / "trace.json").read_text(encoding="utf-8"))
    assert len(saved["steps"]) == len(saved["tool_results"])
    assert saved["tool_results"][1]["name"] == "run_tests"
    assert saved["tool_results"][1]["target"] == saved["steps"][1]["action_target"]


def test_recorded_sieve_t1_baseline_writes_raw_result_pair_for_each_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    root = Path.cwd()
    run_dir, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )

    assert (run_dir / "trace.json").is_file()
    assert [(result.output, result.succeeded) for result in trace.tool_results] == [
        ("edited", True),
        ("tests passed\n", True),
    ]


def test_recorded_sieve_t1_baseline_writes_raw_result_pair_for_each_step_system(
    tmp_path: Path,
) -> None:
    root = Path.cwd()
    run_dir, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )

    saved = TraceRecord.model_validate_json(
        (run_dir / "trace.json").read_text(encoding="utf-8")
    )
    assert len(saved.steps) == len(saved.tool_results) == 2
    assert saved.tool_results[1].name == PlannedAction.RUN_TESTS
    assert saved.tool_results[1].target == "npm test"
    assert trace.tool_results == saved.tool_results


def test_tool_result_pairing_smoke_recorded_sieve_t1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    root = Path.cwd()
    _, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )
    assert len(trace.tool_results) == len(trace.steps) == 2


def test_persisted_tool_result_pair_order_matches_step_action_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    root = Path.cwd()
    _, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )
    assert all(
        step.planned_action == result.name and step.action_target == result.target
        for step, result in zip(trace.steps, trace.tool_results, strict=True)
    )


def test_recorded_sieve_t1_tool_result_pairs_match_phase2_golden_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    root = Path.cwd()
    _, trace = TaskRunner(root, tmp_path / "runs").run(
        "SIEVE-T1", RecordedBackend.from_file(root / "tasks/SIEVE-T1/recorded_run.json")
    )
    expected = json.loads(
        (root / "tests/fixtures/phase2/SIEVE-T1-tool-result-pairs.json").read_text(
            encoding="utf-8"
        )
    )
    assert [result.model_dump(mode="json") for result in trace.tool_results] == expected


def test_cli_run_trace_contains_raw_tool_result_pairs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def successful_vitest(*args: object, **kwargs: object) -> CompletedProcess[str]:
        del args, kwargs
        return CompletedProcess("npm test", 0, stdout="tests passed\n", stderr="")

    monkeypatch.setattr("sieve.runner.subprocess.run", successful_vitest)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sieve",
            "run",
            "--task",
            "SIEVE-T1",
            "--runs-dir",
            str(tmp_path / "runs"),
        ],
    )

    cli.main()

    trace_path = Path(capsys.readouterr().out.split("trace=", 1)[1].strip())
    trace = TraceRecord.model_validate_json(trace_path.read_text(encoding="utf-8"))
    assert len(trace.tool_results) == len(trace.steps) == 2
    assert trace.tool_results[1].target == "npm test"
