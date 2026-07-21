# Methodology

Sieve is a causal faithfulness auditor for coding agents. It tests whether an agent's stated rationale was necessary for a particular software outcome by editing that rationale mid-run and observing the counterfactual result.

## Architecture and evidence

Sieve separates three layers: an agent runner captures the trace and local tool actions; the intervention engine edits one target field and resumes from that point; and the reporting layer compares outputs and renders a static report. Every trace, diff, and score is persisted as JSON under `runs/<run_id>/`, allowing a recorded audit to be regenerated from stored artifacts.

Each reasoning step has fixed fields: `claim`, `constraint`, `hypothesis`, `planned_action`, `action_target`, and `success_criterion`. Structured fields make a single, auditable intervention possible without treating loose prose as a metric.

## Intervention mechanics

For one target step, Sieve either deletes a claim (INT-01), replaces a constraint with a plausible alternative (INT-02), or flips a hypothesis (INT-03). Steps before the target are replayed verbatim as fixed context. Sieve then resumes the run, preserving the baseline alongside the perturbed trace and raw tool results.

## What is measured

Sieve compares the final TypeScript patches with an AST-level distance, so formatting changes do not dominate the result. It also compares the sets of passing and failing task tests. The headline outcome grid answers two questions: did the patch change, and did test outcomes stay stable?

The task suite contains five isolated TypeScript fixtures: two bug fixes, two constrained refactors, and one test-generation task. Each is evaluated against the three single-field interventions.

## Recorded evidence versus live mode

The public report and replay use reviewed recordings. They are deterministic, require no API key, and make no model call at view time. A direct API `--live` mode exists only for manual smoke checks; it can incur cost, varies between runs, and is never used in CI or substituted for the recorded Build Week evidence.

## Limits

Behavioral insensitivity is evidence that a stated field was not necessary for the observed output. It is not a mechanistic account of model computation. The schema is a deliberate simplification of reasoning, and the five-task suite is a proof of concept rather than a benchmark.
