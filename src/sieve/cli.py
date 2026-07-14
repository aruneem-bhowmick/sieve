"""Command-line entry point for the Phase 0 baseline runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from sieve.agent import CodingAgentBackend, OpenAIResponsesBackend, RecordedBackend
from sieve.runner import TaskRunner


def build_parser() -> argparse.ArgumentParser:
    """Build the Phase 0 command-line parser."""
    parser = argparse.ArgumentParser(prog="sieve")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run one task and write a baseline trace")
    run.add_argument("--task", required=True)
    run.add_argument("--live", action="store_true", help="use the OpenAI Responses API")
    run.add_argument("--model", default="gpt-5.6")
    run.add_argument("--runs-dir", type=Path, default=Path("runs"))
    return parser


def main() -> None:
    """Run the requested baseline task and print its persisted trace path."""
    args = build_parser().parse_args()
    root = Path.cwd()
    if args.command != "run":
        raise ValueError(f"unsupported command: {args.command}")
    if args.live:
        backend: CodingAgentBackend = OpenAIResponsesBackend(args.model)
    else:
        recording = root / "tasks" / args.task / "recorded_run.json"
        backend = RecordedBackend.from_file(recording)
    run_dir, trace = TaskRunner(root, root / args.runs_dir).run(args.task, backend)
    print(f"run_id={trace.run_id}")
    print(f"trace={run_dir / 'trace.json'}")


if __name__ == "__main__":
    main()
