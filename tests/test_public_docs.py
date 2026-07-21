"""Regression checks for the public release documentation."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_the_verified_offline_audit_path() -> None:
    """Acceptance: users can set up and run the default audit without an API key."""
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

    assert (
        "Existing tools inspect an agent's reasoning. Sieve intervenes on it and "
        "measures whether the code actually follows."
    ) in readme
    assert 'python -m pip install -e ".[dev]"' in readme
    assert "npm ci" in readme
    assert (
        "python -m sieve run-suite --runs-dir runs/release-audit "
        "--report-path report.html"
    ) in readme
    assert "This command never calls a model API" in readme
    assert "Start-Process $report" in readme
    assert "npm run demo:preview" in readme
    assert "--live" in readme


def test_changelog_separates_shipped_core_from_deferred_roadmap() -> None:
    """Regression: public capability claims distinguish delivery from proposals."""
    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Shipped Build Week Core (Phases 0–4)" in changelog
    assert "## Deferred Roadmap (Phases 5–7)" in changelog
    assert "These proposals are not shipped capabilities." in changelog
