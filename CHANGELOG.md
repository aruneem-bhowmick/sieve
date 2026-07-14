# Changelog

All notable changes to Sieve are documented here. Entries are organized by the
delivery increments that make the causal-faithfulness workflow progressively
more useful. Planned entries describe intended, reviewable scope; they are not
claims that the capability has shipped.

## Unreleased

### Skeleton — Implemented

The project now provides a runnable baseline foundation for capturing a coding
agent's structured rationale and resulting software artifact.

#### Added

- Python packaging, strict linting and typing, GitHub Actions CI, and an 80%
  minimum branch-coverage gate.
- Pydantic contracts for structured reasoning steps, trace records,
  intervention metadata, and test outcomes.
- Validation for task-local increasing step IDs, duplicate test IDs, and
  contradictory pass/fail results.
- Disk persistence for trace JSON, final unified diffs, and isolated
  `runs/<run_id>/` workspaces.
- A deterministic recorded agent backend for local development and CI.
- A direct OpenAI Responses API backend for manual live validation.
- A local task runner with action/plan consistency checks, workspace path
  containment, a bounded step budget, and test-result capture.
- `sieve run --task SIEVE-T1` for recorded baseline execution.
- The first TypeScript/Vitest fixture: an undefined-input bug fix that
  preserves the function's public signature.
- Unit, integration-boundary, CLI, persistence, safety, and error-path tests.
- Contributor workflow documentation for ideator/executor planning and
  concurrency-safe implementation waves.

### Resume and Replay — Planned

This increment will demonstrate that an agent can continue coherently from an
arbitrary trace step before any rationale is altered.

#### Planned changes

- Reconstruct all prior steps as fixed conversational context.
- Resume generation from a selected step and persist the continuation as a
  paired run artifact.
- Add a no-op replay acceptance test that reproduces a baseline final diff
  within defined tolerance.
- Add a resume-specific step budget to bound time and API cost.
- Add recorded replay fixtures for deterministic regression testing.

### Intervention Core — Planned

This increment will create the first causal trace pairs by editing exactly one
stated rationale field and observing the resulting trajectory.

#### Planned changes

- Implement claim deletion: blank one `claim` field and resume execution.
- Implement constraint swapping with task-authored plausible alternatives.
- Persist raw local tool-call results alongside their associated reasoning
  steps.
- Store complete intervention metadata, including target step, field,
  original value, and replacement value.
- Add baseline/perturbed regression fixtures for the first bug-fix and
  constraint-sensitive refactor tasks.

### Scoring and Diffing — Planned

This increment will convert paired run artifacts into interpretable evidence.

#### Planned changes

- Parse changed TypeScript blocks with tree-sitter and compute normalized
  AST-level patch divergence.
- Compare exact test pass/fail identifier sets for outcome stability.
- Persist one score record per task/intervention pair.
- Detect degenerate score batches that could indicate a broken diff,
  ineffective intervention, or task suite with no causal signal.
- Add golden trace-pair regression tests that prevent silent metric drift.

### Full Suite and Report — Planned

This increment will produce the Build Week demonstration artifact.

#### Planned changes

- Add the hypothesis-flip intervention.
- Add the remaining TypeScript fixtures: boundary bug fixing, public API
  compatibility refactoring, and held-out edge-case test generation.
- Add one command to execute the complete baseline/intervention matrix.
- Generate a self-contained `report.html` with a patch-change/test-stability
  2x2, per-task score table, and the product's honest limitations.
- Add static report rendering and visual regression coverage.

## Deferred Roadmap

### Cross-Step and Multi-Model Auditing

- Move justification between unrelated steps to detect post-hoc rationales.
- Compare results across model backends while preserving the same task and
  intervention contracts.

### Evaluation-Framework Interoperability

- Expose the intervention mechanism for use from established evaluation
  systems without surrendering Sieve's artifact and reproducibility model.

### Benchmark Rigor

- Expand the task suite, run multiple seeds, calculate confidence intervals,
  and package the methodology as a citable experimental artifact.
