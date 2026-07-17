"""Bootstrap coverage for local TypeScript fixture tooling."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sieve.fixture_tools import (
    FixtureToolingUnavailable,
    fixture_command_environment,
    path_environment_key,
)


def test_fixture_command_environment_exposes_pinned_tools_and_restores_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unit: copied workspaces inherit the repository's pinned command bin."""
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    path_key = path_environment_key()
    monkeypatch.setenv(path_key, "existing-path")
    monkeypatch.setattr("sieve.fixture_tools.shutil.which", lambda name: name)

    with fixture_command_environment(tmp_path):
        assert os.environ[path_key] == f"{bin_dir}{os.pathsep}existing-path"

    assert os.environ[path_key] == "existing-path"


def test_fixture_command_environment_explains_missing_node_prerequisite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unit: a missing npm executable names the prerequisite and recovery."""
    monkeypatch.setattr("sieve.fixture_tools.shutil.which", lambda _: None)

    with pytest.raises(FixtureToolingUnavailable, match=r"Node\.js.*npm ci"):
        with fixture_command_environment(tmp_path):
            pass


def test_fixture_command_environment_explains_missing_pinned_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Smoke: a skipped dependency install has an actionable recovery command."""
    monkeypatch.setattr("sieve.fixture_tools.shutil.which", lambda name: name)

    with pytest.raises(FixtureToolingUnavailable, match=r"Run npm ci"):
        with fixture_command_environment(tmp_path):
            pass
