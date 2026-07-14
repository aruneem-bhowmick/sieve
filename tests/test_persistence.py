from pathlib import Path
from uuid import uuid4

import pytest

from sieve.persistence import create_run_directory, write_trace
from sieve.schemas import InterventionMetadata, TestResult, TraceRecord


def test_persistence_creates_run_directory_and_writes_trace(tmp_path: Path) -> None:
    run_id = uuid4()
    run_dir = create_run_directory(tmp_path, run_id)
    trace = TraceRecord(
        task_id="SIEVE-T1",
        run_id=run_id,
        run_type="baseline",
        intervention=InterventionMetadata(),
        steps=[],
        final_diff="",
        test_result=TestResult(passed=[], failed=[]),
    )
    path = write_trace(run_dir, trace)
    assert path == run_dir / "trace.json"
    assert '"task_id": "SIEVE-T1"' in path.read_text(encoding="utf-8")


def test_persistence_rejects_reused_run_id(tmp_path: Path) -> None:
    run_id = uuid4()
    create_run_directory(tmp_path, run_id)
    with pytest.raises(FileExistsError):
        create_run_directory(tmp_path, run_id)
