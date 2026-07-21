# Sieve Implementation Guide

This guide is the day-to-day operating manual for building Sieve with the
ideator/executor model. It explains how to turn a Sieve development phase into
small, reproducible implementation jobs, execute them safely, and prove the
result is ready for the next increment.

Sieve is a causal faithfulness auditor for coding agents. Its core question is
practical: when an agent states a claim, constraint, or hypothesis before
changing code, does editing that stated rationale change the patch or outcome?
The project must preserve enough evidence to answer that question from stored
artifacts, not from a later recollection of the run.

## Operating Principles

1. **Keep planning and implementation separate.** The ideator converts an
   approved requirement set into precise executor jobs. Executors implement
   only their assigned job and report deviations instead of resolving design
   ambiguity by themselves.
2. **Use counterfactuals, not prose scoring.** Trace text is input to an
   intervention. The meaningful output is AST-level patch divergence plus test
   outcome stability.
3. **Treat contracts as durable evidence.** Existing trace and score fields
   are additive-only. Use an ADR before changing a field's meaning, removing a
   field, or replacing a binding technical standard.
4. **Make deterministic validation the default.** Recorded backends and
   golden traces belong in tests and CI. Live API calls are manual smoke tests,
   never merge gates.
5. **Finish one dependency wave before starting the next.** Parallelism is
   safe only when executor write sets are disjoint and no executor consumes a
   sibling's unfinished work.

## Roles

| Role | Responsibility | Must not do |
|---|---|---|
| `sieve_ideator` | Read the current requirements, create detailed prompt files, assign dependency-safe waves, and resolve planning ambiguity. | Implement application code or silently change a contract. |
| `sieve_executor` | Read one prompt and its preamble, modify only listed files, add all specified tests, run checks, and report results. | Plan adjacent work, alter undeclared files, or resolve ambiguous requirements independently. |
| Integrator | Review executor reports, run the full checkpoint, merge safe work, and decide whether a phase DoD is met. | Start a later wave while a dependency, test failure, or deviation remains unresolved. |

The repository definitions in `.codex/agents/` enforce the intended split.
`AGENTS.md` is the project-wide operating contract. The more detailed
execution mechanics are in `docs/development/workflow/IDEATOR-EXECUTOR-WORKFLOW.md`.

## One-Time Setup

Run these commands from the repository root:

```powershell
python -m pip install -e ".[dev]"
npm ci
python -m pytest -v
python -m ruff check .
python -m black --check .
python -m mypy --strict .
```

For live manual runs, set `OPENAI_API_KEY`. Recorded runs remain the default:

```powershell
sieve run --task SIEVE-T1
sieve run --task SIEVE-T1 --live --model <model-id>
```

Use a branch per coherent change. Keep generated `runs/`, Python caches, and
Node dependencies out of commits. Retain selected run directories only when
they are deliberately promoted to golden regression fixtures.

## The Development Loop

### 1. Establish the starting point

Before planning a phase, verify all of the following:

- The repository's requirements document is current and complete.
- The preceding phase's Definition of Done is actually met.
- The current branch is clean and all quality checks pass.
- Any contract or standards change has an ADR in `docs/adr/`.
- The target phase is still within Build Week scope; defer optional expansion.

Do not plan around a failing predecessor. Repair or explicitly re-plan it
first; otherwise every later prompt will inherit an invalid assumption.

### 2. Ask the ideator to generate the implementation package

The ideator creates `docs/development/prompts/phase-<N>/` containing:

- `_PREAMBLE.md` with the phase goal, contracts, standards, and test taxonomy.
- One self-contained prompt per requirement ID.
- `INDEX.md` with execution order and dependencies.
- `traceability.md` mapping every requirement to a prompt and test coverage.
- `WAVES.md` with concurrency-safe executor groups.

Each requirement prompt must list exact files it reads and writes, concrete
interfaces, a phase-specific Definition of Done, and all ten test categories.
An inapplicable category must say `N/A — <reason>` rather than being omitted.

### 3. Review the plan before implementation

Review `INDEX.md`, `traceability.md`, and `WAVES.md` as an integrator. Reject
the plan and return it to the ideator if any of these conditions fail:

- A requirement has no prompt, or a prompt has no source requirement.
- A prompt assumes an interface that is neither existing nor specified.
- Two prompts in one wave write the same file.
- A dependency edge points from a later wave to an earlier unfinished wave.
- A prompt changes a data contract without an ADR.
- Test coverage is generic, incomplete, or missing an explicit N/A reason.

### 4. Run executors one wave at a time

Start one `sieve_executor` per prompt in the current wave. Include the exact
prompt path in the assignment. The executor must not work beyond its declared
write set, even when a nearby cleanup appears attractive.

When all executors finish, collect these fields from each report:

- Requirement ID.
- Files created or modified.
- Commands run and pass/fail result.
- Explicit `deviation_flag` status.
- Any blocked dependency or requirement ambiguity.

### 5. Perform the integration checkpoint

Run the full project gate after every wave:

```powershell
python -m pytest -v
python -m ruff check .
python -m black --check .
python -m mypy --strict .
```

Then inspect the diff, executor reports, and changed contract fixtures. Do not
advance until all checks pass and every deviation is resolved. If an executor
reports ambiguity, route that information back to the ideator and regenerate
the affected prompt; do not ask an executor to guess.

### 6. Close the phase deliberately

After the final wave, run phase-specific acceptance and smoke checks. Confirm
the Definition of Done against actual artifacts, then create a reviewable PR.
The PR should state the causal capability added, the evidence produced, test
coverage, and any deliberate exclusions. It should not claim more than the
current evidence supports.

## Reusable Prompt Templates

Replace every bracketed value before sending a template. Preserve the role
names exactly so the installed agent definitions are used.

### Plan a phase

```text
Use sieve_ideator to plan Phase [PHASE_NUMBER] — [PHASE_NAME] for Sieve.

Read the repository requirements document, AGENTS.md, and the
sieve-phase-planner skill before planning. Confirm that Phase
[PREDECESSOR_NUMBER] Definition of Done is met, or report the exact unmet
condition and stop.

Generate docs/development/prompts/phase-[PHASE_NUMBER]/ with _PREAMBLE.md, one complete
prompt per requirement, INDEX.md, traceability.md, and WAVES.md. Apply the
full self-check from the phase-planner skill. In particular, prove that write
sets are disjoint within every wave and that each prompt covers all ten test
types with concrete tests or explicit N/A reasons.

At completion, report: prompt count, wave count, widest wave, dependency
risks, contract/ADR concerns, and the exact phase Definition of Done evidence
the executors must produce. Do not implement application code.
```

### Request a plan review

```text
Review docs/development/prompts/phase-[PHASE_NUMBER]/ as the Sieve integrator.

Check every prompt against its source requirement, the data contracts, binding
standards, and the phase Definition of Done. Mechanically compare prompt write
sets within each wave. Verify that traceability.md contains every requirement
exactly once and that no test-type row is silently omitted.

Return one of:
1. APPROVED — list the wave order and executor count for each wave; or
2. REPLAN REQUIRED — list each defect by prompt path, explain why it blocks
   implementation, and give the exact correction needed.

Do not implement code or broaden scope during this review.
```

### Execute one wave

```text
Spawn one sieve_executor for every prompt in
docs/development/prompts/phase-[PHASE_NUMBER]/WAVES.md Wave [WAVE_NUMBER].

For each executor, provide its exact prompt path:
- [PROMPT_PATH_1]
- [PROMPT_PATH_2]
- [PROMPT_PATH_N]

Each executor must read _PREAMBLE.md first, honor its declared write set,
implement every non-N/A test case, and report requirement ID, files touched,
commands run, tests passed, and deviation_flag. Do not start another wave yet.
```

### Integrate a completed wave

```text
Act as the Sieve integrator for Phase [PHASE_NUMBER], Wave [WAVE_NUMBER].

Collect every executor report. Stop immediately for any deviation_flag,
out-of-scope write, unresolved dependency, or contract ambiguity. If stopped,
summarize the issue for sieve_ideator and do not begin Wave [NEXT_WAVE_NUMBER].

If reports are clean, run:
  python -m pytest -v
  python -m ruff check .
  python -m black --check .
  python -m mypy --strict .

Inspect the git diff and report whether the wave is accepted. State the next
eligible wave and its prerequisites. Do not change application code.
```

### Handle an ambiguity or failed executor job

```text
Use sieve_ideator to repair planning for Phase [PHASE_NUMBER].

Executor [REQUIREMENT_ID] reported: [EXACT_FAILURE_OR_AMBIGUITY].
Affected files: [PATHS]. Current wave: [WAVE_NUMBER].

Determine whether the problem is a missing interface, incorrect dependency,
write-set collision, data-contract conflict, incomplete test specification, or
an ADR-required standards change. Update only the phase prompt package and
wave plan as necessary. Preserve completed prompts unless they are directly
invalidated. Report the revised prompt paths, waves, dependencies, and the
reason the revised plan is now safe to execute.
```

### Confirm completion and prepare a PR

```text
Verify Phase [PHASE_NUMBER] — [PHASE_NAME] is complete.

Compare implementation artifacts with its Definition of Done. Run all project
checks plus these acceptance commands:
[ACCEPTANCE_COMMAND_1]
[ACCEPTANCE_COMMAND_2]

Report: requirements satisfied, artifacts created, test results, coverage,
known limitations, and anything intentionally deferred. If every requirement
is met, draft a PR description focused on the capability, causal evidence,
validation, and honest limits. If not, list the exact remaining work without
claiming completion.
```

## Delivery Sequence

| Stage | Outcome to prove | Primary evidence |
|---|---|---|
| Skeleton | A task produces a well-formed persisted baseline trace. | `trace.json`, isolated workspace, CLI smoke test. |
| Resume and replay | Unedited resumption preserves the original result. | No-op replay golden fixture and final-diff comparison. |
| Intervention core | Claim deletion and constraint swaps create valid perturbed traces. | Paired baseline/perturbed run records. |
| Scoring | Trace pairs become stable, interpretable metrics. | AST divergence, outcome stability, golden score fixtures. |
| Full suite and report | The full task/intervention matrix produces a standalone demonstration artifact. | `report.html`, score records, real 2x2 summary. |
| Post-event maturity | Cross-step, multi-model, framework, and benchmark work. | New ADR-backed requirements and expanded regression evidence. |

## Test Expectations

Every requirement must explicitly address all of these categories:

| Type | Required focus |
|---|---|
| Unit | Pure validation, transforms, normalization, and scoring logic. |
| Integration | Boundaries between runner, intervention, metrics, and reporting. |
| System | One real pipeline path over a fixture without replacing internal layers. |
| Acceptance | Evidence that the stage Definition of Done is met. |
| Smoke | The fastest meaningful CLI or artifact check. |
| Sanity | Range, non-degeneracy, and plausibility checks. |
| Regression | Recorded/golden traces and stable known scores without live API calls. |
| End-to-end | CLI invocation through persisted output or report. |
| API | Request shape, response parsing, schema enforcement, and replay calls; mock in CI. |
| UI | Static report rendering, score-table population, and screenshot/non-blank checks. |

Use the existing 80% branch coverage gate as a floor, not as a reason to omit
the higher-level tests above. Coverage measures exercised lines; it does not
prove causal methodology is sound.

## Jetson Orin Nano Operating Notes

- Use the Jetson as an orchestration host. The OpenAI API performs live model
  inference; the device runs Python, TypeScript fixtures, tree-sitter, and
  static report generation.
- Keep the virtual environment, Node dependencies, and `runs/` directory on
  SSD or external storage where possible. Repeated task workspaces and stored
  traces will outgrow eMMC quickly.
- Keep live concurrency low. Baselines and perturbations should be queued so
  cost, rate limits, and device resource use remain observable.
- Persist the API model identifier, seed where supported, task version, and
  intervention metadata with every run.
- Promote selected live artifacts to golden fixtures only after manually
  reviewing that they are valid examples. Never put credentials or raw secrets
  in run artifacts.

## Scope Guardrails

For the Build Week deliverable, prioritize a small, defensible causal loop:
structured trace, controlled intervention, paired outcome, AST-aware patch
comparison, test stability, and a static report. Do not expand into a general
evaluation platform until this loop works end to end on the fixed task suite.

The product claim must remain precise: behavioral insensitivity shows that the
stated field was not necessary for that observed output. It is not a
mechanistic account of an agent's hidden computation.
