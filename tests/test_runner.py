import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from sieve.agent import AgentTurn, RecordedBackend, ToolInvocation
from sieve.runner import TaskRunner, _workspace_path, unified_directory_diff
from sieve.schemas import PlannedAction, StructuredReasoningStep


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
