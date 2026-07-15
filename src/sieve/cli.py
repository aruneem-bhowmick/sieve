"""Command-line entry point for the Phase 0 baseline runner."""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

from sieve.agent import (
    CodingAgentBackend,
    InterventionCodingAgentBackend,
    OpenAIResponsesBackend,
    RecordedBackend,
    ResumableCodingAgentBackend,
)
from sieve.interventions import (
    ClaimDeletion,
    ConstraintSwap,
    HypothesisFlip,
    InterventionRunner,
)
from sieve.resume import ResumeRunner
from sieve.runner import TaskRunner
from sieve.schemas import TraceRecord
from sieve.scoring import ScoreRunner
from sieve.suite import run_suite


def build_parser() -> argparse.ArgumentParser:
    """Build the Phase 0 command-line parser."""
    parser = argparse.ArgumentParser(prog="sieve")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run one task and write a baseline trace")
    run.add_argument("--task", required=True)
    run.add_argument("--live", action="store_true", help="use the OpenAI Responses API")
    run.add_argument("--model", default="gpt-5.6")
    run.add_argument("--runs-dir", type=Path, default=Path("runs"))
    resume = subparsers.add_parser("resume", help="resume one baseline trace")
    resume.add_argument("--baseline-run-dir", type=Path, required=True)
    resume.add_argument("--step", required=True)
    resume.add_argument("--runs-dir", type=Path, default=Path("runs"))
    resume.add_argument("--max-resumed-steps", type=int, default=20)
    resume.add_argument(
        "--live", action="store_true", help="use the OpenAI Responses API"
    )
    resume.add_argument("--model", default="gpt-5.6")
    intervene = subparsers.add_parser("intervene", help="run one trace intervention")
    intervene.add_argument("--baseline-run-dir", type=Path, required=True)
    intervene.add_argument("--step", required=True)
    intervene.add_argument(
        "--type", choices=["INT-01", "INT-02", "INT-03"], required=True
    )
    intervene.add_argument("--runs-dir", type=Path, default=Path("runs"))
    intervene.add_argument("--max-resumed-steps", type=int, default=20)
    intervene.add_argument(
        "--live", action="store_true", help="use the OpenAI Responses API"
    )
    intervene.add_argument("--model", default="gpt-5.6")
    score = subparsers.add_parser("score", help="score one baseline/perturbed pair")
    score.add_argument("run_id_baseline", type=UUID)
    score.add_argument("run_id_perturbed", type=UUID)
    score.add_argument("--runs-dir", type=Path, default=Path("runs"))
    suite = subparsers.add_parser("run-suite", help="run the full recorded suite")
    suite.add_argument("--runs-dir", type=Path, default=Path("runs"))
    suite.add_argument("--report-path", type=Path, default=Path("report.html"))
    suite.add_argument(
        "--live", action="store_true", help="use the OpenAI Responses API"
    )
    suite.add_argument("--model", default="gpt-5.6")
    suite.add_argument("--short", action="store_true", help="run SIEVE-T1 INT-01 only")
    return parser


def main() -> None:
    """Run the requested baseline task and print its persisted trace path."""
    args = build_parser().parse_args()
    root = Path.cwd()
    if args.command == "run":
        if args.live:
            backend: CodingAgentBackend = OpenAIResponsesBackend(args.model)
        else:
            recording = root / "tasks" / args.task / "recorded_run.json"
            backend = RecordedBackend.from_file(recording)
        run_dir, trace = TaskRunner(root, root / args.runs_dir).run(args.task, backend)
    elif args.command == "resume":
        baseline_run_dir = root / args.baseline_run_dir
        trace_path = baseline_run_dir / "trace.json"
        if not trace_path.is_file() or not (baseline_run_dir / "checkpoints").is_dir():
            raise ValueError(
                "baseline run directory must contain trace.json and checkpoints"
            )
        baseline = TraceRecord.model_validate_json(
            trace_path.read_text(encoding="utf-8")
        )
        if args.live:
            resume_backend: ResumableCodingAgentBackend = OpenAIResponsesBackend(
                args.model
            )
        else:
            recording = root / "tasks" / baseline.task_id / "recorded_resume_run.json"
            resume_backend = RecordedBackend.from_file_from_step(recording, args.step)
        run_dir, trace = ResumeRunner(
            root, root / args.runs_dir, args.max_resumed_steps
        ).resume(baseline, baseline_run_dir, args.step, resume_backend)
    elif args.command == "intervene":
        baseline_run_dir = root / args.baseline_run_dir
        trace_path = baseline_run_dir / "trace.json"
        if not trace_path.is_file() or not (baseline_run_dir / "checkpoints").is_dir():
            raise ValueError(
                "baseline run directory must contain trace.json and checkpoints"
            )
        baseline = TraceRecord.model_validate_json(
            trace_path.read_text(encoding="utf-8")
        )
        if args.live:
            intervention_backend: InterventionCodingAgentBackend = (
                OpenAIResponsesBackend(args.model)
            )
        else:
            suffix = {
                "INT-01": "int01",
                "INT-02": "int02",
                "INT-03": "int03",
            }[args.type]
            recording = (
                root / "tasks" / baseline.task_id / f"recorded_{suffix}_run.json"
            )
            intervention_backend = RecordedBackend.from_file(recording)
        task_dir = root / "tasks" / baseline.task_id
        intervention: ClaimDeletion | ConstraintSwap | HypothesisFlip
        if args.type == "INT-01":
            intervention = ClaimDeletion()
        elif args.type == "INT-02":
            intervention = ConstraintSwap.from_task_fixture(task_dir)
        else:
            intervention = HypothesisFlip.from_task_fixture(task_dir)
        run_dir, trace = InterventionRunner(
            root, root / args.runs_dir, args.max_resumed_steps
        ).run(
            baseline,
            baseline_run_dir,
            args.step,
            intervention,
            intervention_backend,
        )
    elif args.command == "score":
        score_path, _ = ScoreRunner(root / args.runs_dir).score(
            args.run_id_baseline, args.run_id_perturbed
        )
        print(f"score={score_path}")
        return
    elif args.command == "run-suite":
        result = run_suite(
            root,
            root / args.runs_dir,
            root / args.report_path,
            live=args.live,
            model=args.model,
            short=args.short,
        )
        if args.short:
            print(f"report={result.report_path}")
        else:
            print(f"baselines={len(result.baseline_run_ids)}")
            print(f"perturbed={len(result.perturbed_run_ids)}")
            print(f"scores={len(result.score_paths)}")
            print(f"report={result.report_path}")
        return
    else:
        raise ValueError(f"unsupported command: {args.command}")
    print(f"run_id={trace.run_id}")
    print(f"trace={run_dir / 'trace.json'}")


if __name__ == "__main__":
    main()
