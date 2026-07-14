# AGENTS.md — Sieve

## What this project is

Sieve is a causal faithfulness auditor for coding agents (OpenAI Build Week,
Developer Tools track). Full vision, architecture, data contracts, phase
plan, and requirement IDs live in `SIEVE-SPEC.md` at the repo root — read it
before making any architectural decision, and never contradict it. Spec
changes follow the ADR process in `SIEVE-SPEC.md` §14.

## Repository expectations

- Language: Python 3.11+ for orchestration (Layers 1–3). Task suite fixtures
  are TypeScript (see `SIEVE-SPEC.md` §8–9).
- Run `ruff check . && black --check . && mypy --strict .` before considering
  any change complete.
- Run `pytest -v` and confirm it passes before considering any change
  complete. Do not skip this step — verify, don't assume.
- Every trace, diff, and score record is written to `runs/<run_id>/` as JSON
  per `SIEVE-SPEC.md` §5. Never alter the shape of an existing data contract
  without an ADR — additive fields only.
- Task suite fixtures live under `tasks/<task_id>/{src, tests, task.md}` and
  must remain isolated from Layer 1–3 code (adding a task should never
  require touching the harness — this is a Phase 0 acceptance criterion,
  SIV-TSK-001).

## Working agreements

- Prefer the structured requirement ID (`SIV-<AREA>-<NNN>`) in commit
  messages and PR titles when a change implements a specific spec
  requirement.
- Every requirement's test coverage must address all ten test types defined
  in `SIEVE-SPEC.md` §10, with explicit `N/A — <reason>` for inapplicable
  types. Never silently omit a type.
- Live Codex/GPT-5.6 API calls are never used in CI (`SIEVE-SPEC.md` §8, §10
  API row). CI runs only mocked and golden-regression tests. Live-call smoke
  tests are run manually.
- When planning or building a development phase, use the
  `sieve-phase-planner` skill (`.agents/skills/sieve-phase-planner/SKILL.md`)
  rather than improvising a prompt breakdown — it enforces the standardized,
  exhaustively-tested prompt format this project depends on for
  reproducibility.
- This project uses an ideator/executor subagent split (see
  `docs/workflow/IDEATOR-EXECUTOR-WORKFLOW.md`): a high-reasoning agent
  (`sieve_ideator`) plans a phase into granular prompts; narrow
  lower-cost agents (`sieve_executor`) implement individual prompts
  concurrently. Follow that workflow document's wave-based concurrency
  rules — do not fan out executors across prompts that share a dependency
  edge.

## When correcting a mistake

If a repeated mistake shows up in review, codify the fix here rather than
relying on it being remembered next session.
