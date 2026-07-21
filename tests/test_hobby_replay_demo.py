"""Static Hobby deployment checks for the replay-only browser demo."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_profile_is_static_and_excludes_server_source() -> None:
    """Acceptance: Hobby receives only the deterministic public artifact."""
    profile = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert profile == {
        "buildCommand": (
            "python -m venv .sieve-build-venv && "
            ".sieve-build-venv/bin/python -m pip install -e . && "
            'npm ci && PATH=".sieve-build-venv/bin:$PATH" npm run demo:build'
        ),
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


def test_ci_runs_the_replay_artifact_guard_without_scanning_replay_data() -> None:
    """Regression: CI verifies the built app shell, not task-fixture content."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    verifier = (ROOT / "tools" / "verify_hobby_replay.mjs").read_text(encoding="utf-8")
    vite_config = (ROOT / "web" / "vite.config.ts").read_text(encoding="utf-8")

    assert "- run: npm run test:web" in workflow
    assert "- run: npm run demo:verify" in workflow
    assert '"replay-data"' in vite_config
    assert 'basename(path).startsWith("replay-data-")' in verifier
    assert "appShell.includes(marker)" in verifier


def test_public_docs_describe_no_secret_hobby_deployment() -> None:
    """Documentation regression: operators are directed to safe static replay."""
    deployment_guide_path = ROOT / "docs" / "development" / "vercel-hobby-replay.md"
    deployment_guide = deployment_guide_path.read_text(encoding="utf-8")
    adr = (ROOT / "docs" / "adr" / "0002-vercel-hobby-replay-only.md").read_text(
        encoding="utf-8"
    )

    assert (
        "Do not configure Blob, Redis, OpenAI, Sandbox, session, "
        "worker, or cron" in deployment_guide
    )
    assert "GitHub Pages report" in deployment_guide
    assert "excludes `api/`" in adr
    assert "server-only credentials" in adr
