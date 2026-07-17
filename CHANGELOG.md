# Changelog

All notable changes to Sieve are documented here. The shipped Build Week core
is available now; the roadmap lists ideas that are deliberately not part of
the delivered audit.

## Shipped Build Week Core (Phases 0–4)

### Structured recorded runs

- Python packaging, strict linting and typing, GitHub Actions CI, and an 80%
  minimum branch-coverage gate.
- Pydantic contracts for structured reasoning steps, trace records,
  intervention metadata, test outcomes, and score records.
- Validation for task-local increasing step IDs, duplicate test IDs, and
  contradictory pass/fail results.
- Disk persistence for trace JSON, final unified diffs, score records, and
  isolated `runs/<run_id>/` workspaces.
- A deterministic recorded backend for local development and CI, plus a direct
  OpenAI Responses API backend for optional manual smoke checks.
- A local task runner with action/plan consistency checks, workspace path
  containment, bounded step budgets, and test-result capture.
- Five isolated TypeScript/Vitest task fixtures covering bug fixing,
  constraint-preserving refactors, and edge-case test generation.

### Replay and interventions

- Reconstruct prior trace steps as fixed context and resume from a selected
  step with bounded continuation length.
- Verify no-op replay fidelity against recorded baseline artifacts.
- Apply claim deletion, constraint swap, and hypothesis flip interventions.
- Persist complete intervention metadata and pair each reasoning step with its
  raw local tool results.

### Scoring and evidence

- Compute normalized tree-sitter TypeScript patch divergence for paired runs.
- Compare exact passed and failed test identifier sets for outcome stability.
- Persist one score per task/intervention pair and reject degenerate audit
  batches.
- Maintain recorded trace-pair and score regressions for deterministic checks.

### Complete audit and report

- Run the full five-task, three-intervention recorded matrix with one command.
- Render a self-contained static report containing the patch-change/
  test-stability grid, per-task score table, and honest limitations.
- Cover report generation with static rendering and visual regression checks.

## Deferred Roadmap (Phases 5–7)

These proposals are not shipped capabilities.

### Cross-step and multi-model auditing

- Move a justification between unrelated steps to test for post-hoc rationales.
- Compare results across model backends while preserving the same task and
  intervention contracts.

### Evaluation-framework interoperability

- Expose the intervention mechanism for use from established evaluation
  systems without surrendering Sieve's artifact and reproducibility model.

### Benchmark rigor

- Expand the task suite, run multiple seeds, calculate confidence intervals,
  and package the methodology as a citable experimental artifact.
