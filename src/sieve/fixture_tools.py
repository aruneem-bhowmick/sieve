"""Runtime setup for TypeScript task fixtures copied into run workspaces."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class FixtureToolingUnavailable(RuntimeError):
    """Raised when a recorded task cannot access its local Node tooling."""


def path_environment_key() -> str:
    """Return the PATH spelling already used by the active environment."""
    return "PATH" if "PATH" in os.environ or "Path" not in os.environ else "Path"


@contextmanager
def fixture_command_environment(repo_root: Path) -> Iterator[None]:
    """Expose the repository-pinned Vitest binary to copied task workspaces."""
    if shutil.which("npm") is None:
        raise FixtureToolingUnavailable(
            "Node.js and npm are required to run task fixtures. "
            "Install Node.js 22 or later, then run npm ci."
        )

    bin_dir = repo_root / "node_modules" / ".bin"
    if not bin_dir.is_dir():
        raise FixtureToolingUnavailable(
            "Pinned task tooling is missing. Run npm ci from the repository root "
            "and retry the command."
        )

    path_key = path_environment_key()
    previous = os.environ.get(path_key)
    os.environ[path_key] = (
        f"{bin_dir}{os.pathsep}{previous}" if previous else str(bin_dir)
    )
    try:
        yield
    finally:
        if previous is None:
            del os.environ[path_key]
        else:
            os.environ[path_key] = previous
