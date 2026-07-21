"""Regression checks for the public release documentation and navigation."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(
    r"(?<!!)\[[^]]*\]\(" r"(?P<target><[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)"
)
PUBLIC_SUBMISSION_URLS = (
    "https://www.youtube.com/watch?v=ZrjJlJ-EzrM",
    "https://devpost.com/software/sieve-es0x8f",
    "https://aruneem-bhowmick.github.io/sieve/",
)


def test_readme_documents_the_verified_offline_audit_path() -> None:
    """Acceptance: users can set up and run the default audit without an API key."""
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

    assert '<h1 align="center">Sieve</h1>' in readme
    assert "Sieve tests whether a coding agent's stated rationale" in readme
    assert 'python -m pip install -e ".[dev]"' in readme
    assert "npm ci" in readme
    assert (
        "python -m sieve run-suite --runs-dir runs/release-audit "
        "--report-path report.html"
    ) in readme
    assert "This command never calls a model API" in readme
    assert "without an API key" in readme
    assert "--live" not in readme


def test_readme_and_docs_local_markdown_links_resolve() -> None:
    """Regression: the curated documentation map contains no broken local links."""
    documents = (
        REPOSITORY_ROOT / "README.md",
        *sorted((REPOSITORY_ROOT / "docs").rglob("*.md")),
    )

    for document in documents:
        contents = document.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(contents):
            target = match.group("target").strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            resolved = (document.parent / unquote(parsed.path)).resolve()
            assert (
                resolved.exists()
            ), f"{document.relative_to(REPOSITORY_ROOT)} -> {target}"


def test_readme_exposes_the_three_public_submission_urls() -> None:
    """Acceptance: judges can reach each public submission artifact directly."""
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

    for url in PUBLIC_SUBMISSION_URLS:
        assert url in readme


def test_internal_agent_instructions_use_the_moved_development_paths() -> None:
    """Regression: the ideator/executor workflow cannot recreate retired paths."""
    paths = (
        REPOSITORY_ROOT / ".codex" / "agents" / "sieve-ideator.toml",
        REPOSITORY_ROOT / ".codex" / "agents" / "sieve-executor.toml",
        REPOSITORY_ROOT / ".codex" / "config.toml",
        REPOSITORY_ROOT / ".agents" / "skills" / "sieve-phase-planner" / "SKILL.md",
    )

    for path in paths:
        contents = path.read_text(encoding="utf-8")
        assert "docs/prompts/" not in contents
        assert "docs/workflow/" not in contents


def test_development_docs_cover_pages_setup_and_local_replay_preview() -> None:
    """Acceptance: operators can publish and preview the recorded showcase."""
    guide = (
        REPOSITORY_ROOT / "docs" / "development" / "github-pages-showcase.md"
    ).read_text(encoding="utf-8")

    assert "Settings → Pages → Build and deployment" in guide
    assert "Source** to **GitHub Actions" in guide
    assert "npm run demo:build" in guide
    assert "npm run demo:preview" in guide
    assert "http://127.0.0.1:4173" in guide


def test_changelog_separates_shipped_core_from_deferred_roadmap() -> None:
    """Regression: public capability claims distinguish delivery from proposals."""
    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Shipped Build Week Core (Phases 0–4)" in changelog
    assert "## Deferred Roadmap (Phases 5–7)" in changelog
    assert "These proposals are not shipped capabilities." in changelog
