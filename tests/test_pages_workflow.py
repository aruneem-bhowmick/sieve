"""Regression coverage for the deterministic GitHub Pages build workflow."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pages_workflow_installs_pinned_node_fixture_tooling_before_run_suite() -> None:
    """Pages must install Vitest because run-suite executes copied task fixtures."""
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )
    setup_node = workflow.index("actions/setup-node@v4")
    npm_install = workflow.index("- run: npm ci")
    run_suite = workflow.index("- run: python -m sieve run-suite")

    assert 'node-version: "22"' in workflow
    assert setup_node < npm_install < run_suite
