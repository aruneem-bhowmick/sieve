"""Create the Vite replay input from a fresh, deterministic audit in a temp dir."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from sieve.replay_bundle import write_replay_bundle
from sieve.suite import run_suite


def main() -> None:
    """Run the recorded matrix outside the checkout and export its safe projection."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="sieve-demo-") as temporary:
        location = Path(temporary)
        runs_dir = location / "runs"
        run_suite(root, runs_dir, location / "report.html")
        write_replay_bundle(runs_dir, root / "tasks", args.output)


if __name__ == "__main__":
    main()
