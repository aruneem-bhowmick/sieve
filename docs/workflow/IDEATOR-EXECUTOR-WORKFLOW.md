# Sieve's Ideator/Executor Workflow on Codex

This document is the operational glue between `SIEVE-SPEC.md`, the
`sieve-phase-planner` skill, and the two custom agents
(`.codex/agents/sieve-ideator.toml`, `.codex/agents/sieve-executor.toml`).
It exists because none of those three files alone tells you *how to run
them together* — this does.

## The mapping, at a glance

| Your concept | Codex primitive |
|---|---|
| Advanced model that ideates | `sieve_ideator` custom agent, pinned to `gpt-5.6-terra`, high reasoning effort |
| The "write detailed prompts" step | The `sieve-phase-planner` skill, invoked by `sieve_ideator` |
| Lesser models doing grunt work | `sieve_executor` custom agent, pinned to `gpt-5.4-mini`, medium reasoning effort |
| "Concurrently" | Codex subagent fan-out, either manual (`spawn one agent per...`) or batch (`spawn_agents_on_csv`), capped by `agents.max_threads` in `.codex/config.toml` |
| Not letting concurrent workers collide | The skill's wave assignment (§5 of the skill's workflow) — prompts only run concurrently if their declared write-sets are disjoint |

## Step 1 — Plan the phase

Start a Codex session in the repo root and ask for `sieve_ideator` by name
so the planning work happens on the pinned high-reasoning model, not
whatever Codex would otherwise auto-select:

```
Use sieve_ideator to plan Phase 0 of Sieve using the sieve-phase-planner
skill. Confirm the wave plan before finishing.
```

`sieve_ideator` will read `SIEVE-SPEC.md`, run the skill's full workflow,
and produce `docs/prompts/phase-0/` containing `_PREAMBLE.md`, one prompt
per requirement, `INDEX.md`, `traceability.md`, and `WAVES.md`.

**Check `WAVES.md` yourself before moving on.** It tells you, per wave, how
many prompts can run concurrently — this is the number that determines how
many `sieve_executor` threads to spawn next. For Sieve's Build Week phases,
expect narrow waves early (Phase 0's schema/runner work is mostly
sequential) and wider waves once the task suite expands (Phase 4 has five
largely-independent task fixtures that can genuinely run in parallel).

## Step 2 — Fan out executors, one wave at a time

**Never fan out across waves at once.** A later wave's prompts assume an
earlier wave's files already exist; running them all in one shot reproduces
the exact race condition the wave split exists to prevent.

### Option A — Manual fan-out (default; use this first)

This is the reliable, fully-specified path: it names `sieve_executor`
explicitly, so you're guaranteed the pinned model and sandbox settings from
its TOML file, not whatever Codex would otherwise pick.

```
Spawn one sieve_executor per prompt in docs/prompts/phase-0/WAVES.md wave 1:
- SIV-OPS-001
- SIV-SCH-001
Wait for all of them, then summarize each: requirement ID, files touched,
test pass/fail, and any reported deviation or out-of-scope-write flag.
```

Reference each executor's assigned prompt file by path, not just by ID, so
there's no ambiguity about which file it should be reading.

### Option B — Batch fan-out via `spawn_agents_on_csv` (for wide waves)

For a wave with many independent prompts (e.g. Phase 4's per-task
fixtures), the CSV batch primitive avoids writing out a long manual list.
As of this writing, `spawn_agents_on_csv`'s documented parameters
(`csv_path`, `instruction`, `id_column`, `output_schema`, `output_csv_path`,
`max_concurrency`, `max_runtime_seconds`) don't include an explicit "use
this custom agent" field — **verify against your installed Codex CLI
version whether batch workers inherit `sieve_executor`'s pinned model, or
default to Codex's own model selection**, before relying on this path for
cost control. If it doesn't inherit the pin, Option A is the safer default
until that's confirmed.

If you do use it, the row-to-worker mapping looks like this:

```
Build /tmp/phase0-wave1.csv with columns requirement_id,prompt_path — one
row per prompt in docs/prompts/phase-0/WAVES.md wave 1.

Then call spawn_agents_on_csv with:
- csv_path: /tmp/phase0-wave1.csv
- id_column: requirement_id
- instruction: "You are executing docs/prompts/phase-0/{prompt_path} per
  the sieve_executor role defined in .codex/agents/sieve-executor.toml —
  follow its developer_instructions exactly, including the strict
  file-boundary rule. Read _PREAMBLE.md in the same directory first.
  Report requirement_id, files touched, test pass/fail, and any deviation
  flag via report_agent_job_result."
- output_schema: object with required fields requirement_id, files_touched,
  tests_passed (boolean), deviation_flag
- output_csv_path: /tmp/phase0-wave1-results.csv
```

## Step 3 — Integration checkpoint (mandatory between every wave)

Before moving to the next wave, whoever is orchestrating (you, or the main
Codex thread) must:

1. Run the project's full check: `pytest -v && ruff check . && black
   --check . && mypy --strict .`
2. Read every executor's deviation flag from Step 2. Any flagged deviation
   or out-of-scope write is a stop — do not proceed to the next wave with
   an unresolved flag, even if tests currently pass. An out-of-scope write
   that happens to not break tests today is exactly the kind of silent
   drift the wave-isolation design exists to catch early.
3. If an executor reported an unresolved dependency or spec ambiguity,
   route it back to `sieve_ideator`, not to the executor itself — the
   executor's job is to report ambiguity, not resolve it (see its
   `developer_instructions`), and re-planning is `sieve_ideator`'s job.

Only after a clean checkpoint should you start the next wave.

## Step 4 — Repeat per phase

Once all waves in a phase are complete and the phase's Definition of Done
(`SIEVE-SPEC.md` §13) is met, return to Step 1 for the next phase. Each
phase's `sieve_ideator` invocation should explicitly confirm the prior
phase's DoD before planning the next one — this is worth asking for
directly:

```
Confirm Phase 0's Definition of Done is met (check SIEVE-SPEC.md §13), then
use sieve_ideator to plan Phase 1 with the sieve-phase-planner skill.
```

## Cost and concurrency notes

- `sieve_ideator` on `gpt-5.6-terra` at high reasoning effort is the
  expensive half of this pipeline per-token, but it runs once per phase,
  not once per requirement — the design principle is to spend depth where
  it's cheap in aggregate (one planning pass) rather than where it's
  expensive in aggregate (many implementation passes).
- `sieve_executor` on `gpt-5.4-mini` is deliberately narrow-scoped per the
  research on subagent cost: each concurrent thread does its own full
  model and tool work, so a wide wave genuinely multiplies token spend by
  wave width, not just wall-clock time saved. `agents.max_threads = 6` in
  `.codex/config.toml` is a deliberate cap, not an oversight — if a
  phase's widest wave exceeds it, either raise the cap deliberately or
  accept that wave will run in two batches.
- If a wave is consistently producing deviation flags or failing
  integration checkpoints, that's a signal the phase plan's prompts were
  under-specified, not that the executor model is too weak — escalate to
  re-running `sieve_ideator` on that phase with the failure detail as
  additional context, rather than switching the executor to a stronger
  model as a first response.

## Isolation caveat (read before your first wide wave)

Whether concurrent subagents in your Codex surface (CLI, App, Cloud) write
against fully isolated sandboxes or a shared local working tree depends on
which surface and version you're running — this has been an active area of
change. The wave-disjointness guarantee from the skill (no two prompts in a
wave share a write-set file) is designed to be safe either way, but if
you're on a surface where subagents share a working tree directly, consider
pairing each `sieve_executor` invocation with a git worktree per thread
(the Codex App's Worktrees feature, or `git worktree add` manually in CLI)
as a second layer of protection, merging back at each integration
checkpoint in Step 3.
