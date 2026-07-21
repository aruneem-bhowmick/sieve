"""Generate the browser replay fixture after a deterministic recorded suite."""

from __future__ import annotations

import argparse
from pathlib import Path

from sieve.replay_bundle import write_replay_bundle


def main() -> None:
    """Write one browser-safe replay JSON document from already-persisted runs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--tasks-dir", type=Path, default=Path("tasks"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_replay_bundle(args.runs_dir, args.tasks_dir, args.output)


if __name__ == "__main__":
    main()
