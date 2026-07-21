"""Static Hobby deployment checks for the replay-only browser demo."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_profile_is_static_and_excludes_server_source() -> None:
    """Acceptance: Hobby receives only the deterministic public artifact."""
    profile = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert profile == {
        "buildCommand": "python -m pip install -e . && npm ci && npm run demo:build",
        "outputDirectory": "public",
    }
    assert (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines() == ["api/"]


def test_browser_source_has_no_live_request_or_live_controls() -> None:
    """Regression: local ZIP preparation cannot queue, poll, or invoke a model."""
    source = (ROOT / "web" / "src" / "main.ts").read_text(encoding="utf-8")

    assert "fetch(" not in source
    assert "/api/" not in source
    assert "Unlock live demo" not in source
    assert "Validate & start live suite" not in source
    assert "never runs submitted code" in source
    assert "makes no API or model request" in source


def test_public_docs_describe_no_secret_hobby_deployment() -> None:
    """Documentation regression: operators are directed to safe static replay."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    adr = (ROOT / "docs" / "adr" / "0002-vercel-hobby-replay-only.md").read_text(
        encoding="utf-8"
    )

    assert (
        "Do not configure Blob,\nRedis, OpenAI, Sandbox, session, worker, or cron"
        in readme
    )
    assert "GitHub Pages report" in readme
    assert "excludes `api/`" in adr
    assert "server-only credentials" in adr
