"""Regression coverage for the presenter-safe recorded-demo instructions."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "OFFLINE-DEMO-RUNBOOK.md"


def test_offline_demo_runbook_preserves_the_recorded_suite_and_recovery_contract() -> (
    None
):
    """Acceptance: operators have exact offline execution and recovery guidance."""
    runbook = RUNBOOK.read_text(encoding="utf-8")

    assert (
        "python -m sieve run-suite --runs-dir $runDirectory --report-path "
        "$reportPath" in runbook
    )
    assert "Do not add `--live` to this command." in runbook
    assert "baselines=5" in runbook
    assert "perturbed=15" in runbook
    assert "scores=15" in runbook
    assert "Remove-Item -LiteralPath $demoRoot -Recurse -Force" in runbook


def test_offline_demo_runbook_requires_visible_local_report_and_network_check() -> None:
    """Regression: the runbook verifies the report before it is presented."""
    runbook = RUNBOOK.read_text(encoding="utf-8")

    for required_marker in (
        'id="two-by-two-grid"',
        "<table>",
        "Honest Limitations",
        "Start-Process -FilePath $reportPath",
        "external network reference",
    ):
        assert required_marker in runbook
    assert "optional manual smoke tests only" in runbook
