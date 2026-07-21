---
name: sieve-phase-planner
description: >
  Transform a single phase of SIEVE-SPEC.md into an exhaustive, standardized
  prompt document set — one granular, self-contained implementation prompt
  per requirement ID — each specifying the exact code to write and a
  complete test-suite specification spanning unit, integration, system,
  acceptance, smoke, sanity, regression, end-to-end, API, and UI testing as
  applicable, plus a dependency graph grouped into concurrency-safe waves so
  independent prompts can be executed by parallel subagents. Trigger this
  skill whenever the user asks to plan, break down, decompose, or generate
  prompts/tasks/tickets for a Sieve phase, mentions "phase planning",
  "PHASE-N prompts", "prompt document", "wave plan", or asks to
  start/prepare implementation of any SIV-* requirements — even without
  naming this skill explicitly. This skill is normally invoked by the
  sieve_ideator custom agent, not by executor agents.
---

# Sieve Phase Planner

## Purpose

Sieve is delivered in Agile phases (Phase 0 → 7; see `SIEVE-SPEC.md` §13).
This skill takes **one phase** and expands **every requirement in it** into
a granular implementation prompt, then groups those prompts into
**dependency-safe waves** so that a fleet of narrow executor subagents can
build the phase with maximum safe concurrency and zero file-write
collisions.

The output is a directory of prompts plus a wave plan so complete and
standardized that Codex can execute the entire phase from the prompts
alone — write the code, write every relevant test, and satisfy the phase's
Definition of Done — without re-reading the rest of the spec for missing
detail, and without two concurrent executors ever touching the same file at
the same time.

The three non-negotiables this skill exists to enforce:

1. **Exhaustive testing.** Every prompt specifies concrete tests for *every
   applicable type* from `SIEVE-SPEC.md` §10's ten-type taxonomy and
   explicitly marks inapplicable types as `N/A — <specific reason>`, never
   silently skipped.
2. **Standardization & reproducibility.** Every prompt follows one fixed
   template, inherits one shared phase preamble, references its source
   requirement ID, and is self-contained. Regenerating the same phase from
   an unmodified spec produces the same structure, the same prompt count,
   and the same wave assignment.
3. **Concurrency safety.** Every prompt declares the exact files it reads
   and writes. Two prompts are placed in the same wave only if their
   file-write sets are disjoint and neither is in the other's dependency
   chain. This is what makes it safe to hand a wave to multiple
   `sieve_executor` subagents at once.

## Inputs

Locate these yourself; only ask the user if genuinely not found:

- **The spec.** Default `SIEVE-SPEC.md` at the repo root.
- **The target phase.** A phase number or name (e.g. "Phase 2" /
  "Intervention Core"). Map names to numbers using §13's phase headings.
- **The output location.** Default `docs/development/prompts/phase-<N>/`. Create it if
  absent.

## Workflow

1. **Read the spec in full.** Internalize §5 (Data Contracts — quote
   verbatim, never paraphrase), §6 (Intervention Taxonomy), §7 (Metrics &
   Scoring formulas), §8 (Binding Standards), §10 (Test Taxonomy), and §15
   (Risk Register entries relevant to this phase's requirement areas).

2. **Locate the phase** in §13. Extract objective, increment, `Depends on`,
   Definition of Done, and the full requirement table.

3. **Generate one prompt per requirement**, using the mandated template
   below, splitting only when a requirement has genuinely separable
   deliverables (suffix `SIV-INT-005a`, `SIV-INT-005b`; never merge two
   requirements into one prompt).

4. **Declare file-level read/write sets per prompt** (new section vs. the
   Claude Code version of this skill — see template §"Files to create or
   modify," which is now load-bearing for wave assignment, not just
   documentation).

5. **Build the dependency graph and assign waves.** A prompt depends on
   another if the spec's requirement table implies it (topological
   ordering, same rule as before) *or* if their file-write sets intersect.
   Assign wave numbers: wave 1 = all prompts with no dependencies; wave *k*
   = all prompts whose dependencies are fully satisfied by waves 1..*k*-1.
   Within a wave, no two prompts may share a write-set file — if they do,
   split the wave further even if the spec table didn't imply an ordering
   (this is a correctness rule, not a spec-fidelity rule, and it takes
   precedence).

6. **Write the phase preamble** (`_PREAMBLE.md`).

7. **Write the index, traceability matrix, and wave plan**
   (`INDEX.md`, `traceability.md`, `WAVES.md`).

8. **Run the quality gate** ("Self-check before finishing"). Fix any
   failures before presenting output.

## Phase preamble (`_PREAMBLE.md`)

Quote verbatim from the spec (not paraphrased):

- Phase objective, `Depends on`, increment, and Definition of Done (§13).
- The data contracts this phase touches (§5.1/5.2/5.3 full JSON shapes).
- Intervention mechanics (§6) and metric formulas (§7), if touched.
- Binding standards condensed to a checklist (§8): stack, AST-diffing tool,
  lint/type/format/test commands, persistence layout, CI posture.
- The full ten-type test taxonomy table (§10).
- The dependency-ordered, wave-grouped list of prompts in this phase.

Every prompt begins by instructing the executor to read `_PREAMBLE.md`
first — this is what keeps a narrow `sieve_executor` agent, which never
reads the full spec, fully oriented.

## The prompt template (use this EXACT structure for every prompt)

One markdown file per requirement:
`<requirement-id>-<slug>.md` (e.g. `SIV-INT-005-claim-deletion.md`). Never
leave a placeholder, ellipsis, or "etc." Prefer concrete signatures, exact
paths, explicit assertions.

```markdown
# <Requirement ID> — <Title>

## Traceability
- Phase: <N> — <phase name> (SIEVE-SPEC.md §13)
- Requirement: <verbatim requirement description from the §13 table>
- Wave: <wave number this prompt is assigned to>
- Depends on: <prior SIV-<AREA>-<NNN> IDs, or "none">
- Unblocks: <later SIV-<AREA>-<NNN> IDs, or "none">
- Advances DoD: <the specific phase DoD clause this moves toward>

## Objective
<One paragraph: the concrete capability delivered, tied to the phase
objective/increment and the architecture layer (§4) it belongs to.>

## Context & assumptions
- Read `_PREAMBLE.md` first; inherit all standards, contracts, and test
  taxonomy without restating them.
- <Which data contract(s) from §5 this prompt reads or writes, exact field
  names/types.>
- <What prior prompts (by requirement ID) are assumed to already exist and
  be working.>
- <If this requirement area appears in §15 Risk Register, name the risk and
  how this prompt's design accounts for it.>

## Interface specification
<Written as code. Exact function/class signatures, exact CLI subcommand
shape if applicable, exact new module paths.>

## Files to create or modify (this section is load-bearing for concurrency — see below)
- **Reads:** `path/to/file` — <why>
- **Writes (creates or modifies):** `path/to/file` — <what changes>
- `tests/...` — new test files, mirroring the source path

Exact paths only. No two prompts in the same wave may list the same file
under "Writes."

## Implementation notes
<Anything binding from the spec a generic implementation might get wrong —
quote the exact formula/contract/mechanic, don't paraphrase.>

## Test specification

Address every row. `N/A — <specific reason>` where inapplicable — never
omit a row.

| Type | Test cases |
|---|---|
| Unit | <concrete test names + assertions> |
| Integration | <...or N/A — reason> |
| System | <...or N/A — reason> |
| Acceptance | <...or N/A — reason> |
| Smoke | <...or N/A — reason> |
| Sanity | <...or N/A — reason> |
| Regression | <...or N/A — reason> |
| End-to-end | <...or N/A — reason> |
| API | <...or N/A — reason; note if mocked per §8 CI posture> |
| UI | <...or N/A — reason, per §10's narrow report-only UI scope> |

## Definition of done for this prompt
- [ ] All files listed above exist with the specified interfaces.
- [ ] All non-N/A tests pass locally via <exact command>.
- [ ] `mypy --strict`, `ruff`, `black --check` pass on all new/modified
  files.
- [ ] No data contract in §5 was altered; additive-only changes, noted in
  Traceability if any.
- [ ] Golden/regression fixtures, if authored, are committed with the code
  they characterize.
```

## Output layout

```
docs/development/prompts/phase-<N>/
├── _PREAMBLE.md
├── <requirement-id>-<slug>.md   (one per requirement)
├── ...
├── INDEX.md
├── traceability.md
└── WAVES.md
```

- **`INDEX.md`** — phase objective/increment/DoD, prompts in execution
  order with one-line descriptions and dependency edges.
- **`traceability.md`** — table: `Requirement ID | Prompt file | Wave |
  Depends on | Test types covered | DoD clause advanced`.
- **`WAVES.md`** — new artifact. One section per wave: the prompt IDs in
  that wave, confirmation their write-sets are disjoint, and the exact
  `sieve_executor` fan-out invocation for that wave (see
  `docs/development/workflow/IDEATOR-EXECUTOR-WORKFLOW.md` for the invocation
  template this section should follow).

## Self-check before finishing

1. **Coverage.** Every requirement ID in the target phase has exactly one
   prompt file (or a documented, traceable split).
2. **No silent test omission.** All ten rows populated per prompt, with
   specific (not generic) `N/A` reasons.
3. **No placeholders.** No ellipsis, "TODO," or unresolved bracket text.
4. **Dependency order is acyclic and respected** across waves.
5. **Wave disjointness.** No two prompts in the same wave share a file in
   their "Writes" set. This is checked mechanically, not by inspection —
   diff the write-set lists pairwise within each wave.
6. **Contract fidelity.** Every quoted data contract, formula, or mechanic
   matches `SIEVE-SPEC.md` verbatim.
7. **Standards inheritance.** No prompt specifies a different stack,
   linter, test runner, or layout convention than §8.
8. **Traceability completeness.** `traceability.md` and `WAVES.md` have no
   blank cells and account for every prompt.
9. **Cold-start reproducibility.** Read `INDEX.md` and one arbitrary prompt
   as if a brand-new agent session with no memory of this conversation.
   Confirm `_PREAMBLE.md` + that one prompt file are sufficient to start
   writing code with no implicit reliance on this conversation's context.

## Notes for sieve_ideator

- This skill is the core of your job. Invoke it (or follow it directly)
  whenever asked to plan a phase.
- You do not implement code yourself when running this skill — your output
  is the prompt set and wave plan. Implementation is `sieve_executor`'s job.
- If executing agents downstream report a spec/prompt conflict, that is
  signal this skill's output had a defect — treat it as a bug in the prompt
  generation, not a one-off exception, and consider whether the same defect
  affects other prompts in the phase.
