# Sieve: Test whether a coding agent's stated rationale was actually load-bearing.

Coding agents explain themselves constantly. Sometimes that explanation is a useful account of why the patch looks the way it does. Sometimes the patch would have come out the same without it. Sieve puts that claim to the test by editing one declared reason and seeing what happens to the code.

## The problem

An agent might say it added a guard because an API can return an absent value, or kept a behavior because a public interface depends on it. The patch may be correct. The explanation may still be a tidy story added after the decision. Developers have no good way to tell the difference, and that gap matters when an agent's comments start to carry the weight of a code review.

Sieve runs a small behavioral experiment instead of trying to infer a model's private thoughts. Change one declared reason while holding the task and earlier work fixed. Then look at the result. Did the patch move? Did the tests behave differently? The answer is evidence a developer can inspect and reproduce.

## How it works

The loop is simple: capture, intervene, compare. Before every local tool action, Sieve records a structured step with a claim, constraint, hypothesis, planned action, and success criterion. That fixed shape lets it test a single counterfactual without trying to edit a loose block of prose.

Sieve then changes one field at one step and resumes the run from that point. It can delete a claim, swap in a plausible alternative constraint, or replace a hypothesis with a contradictory alternative. Everything before the edited step stays fixed. The resulting run has an unedited baseline beside it.

The comparison focuses on the software, not the wording. Sieve calculates patch divergence from the TypeScript AST, so formatting changes do not dominate the result, and checks test stability by comparing the pass/fail sets. If changing the declared reason changes the patch or outcome, that reason mattered to this run. If the code stays the same and still works, the field was not needed for that result. Those are bounded conclusions about an observed experiment, not claims about hidden model cognition.

## What judges can explore

The suite has five isolated TypeScript fixtures: two bug fixes, two refactors with constraints, and a test-generation task. Each one gets three single-field interventions. The recorded output includes baselines, perturbed runs, JSON traces, diffs, and score records, so the evidence is available for review rather than disappearing after a demo.

A standalone static HTML report puts every result in a 2x2 grid: did the patch change, and did the tests stay stable? From there, a reviewer can open per-task and per-intervention records instead of taking a summary score on faith.

The interactive replay is intentionally limited. It lets a reviewer inspect the recorded five-by-three evidence and locally prepare, import, or export a five-task suite. It does not execute submitted code, change the stored evidence, or make model/API requests. The public showcase is deterministic recorded evidence. A separate manual `--live` mode can call the direct API with credentials, but those runs are kept apart from public evidence and automated checks.

## GPT-5.6, Codex, and what I learned

Sieve audits Codex/GPT-5.6 through a direct OpenAI Responses API backend. The runner requires the structured step before every local tool action, then saves the trace and its paired result for comparison.

Building Sieve taught me how to get better results from GPT-5.6 and Codex while developing a real project. Structured planning made the work easier to break down. Targeted implementation kept changes narrow. Verification caught assumptions early. And returning to a written specification after each pass kept the project coherent as it grew. Those habits became part of Sieve's design: make the reason explicit, preserve the evidence, and check the outcome.

## Why it matters

Sieve gives developers a way to test an agent's stated reasons instead of treating them as supporting evidence by default. The limits are part of the pitch. It measures behavioral sensitivity, not mechanistic interpretability. Its schema covers a chosen set of fields rather than every part of a model's thinking. And five tasks are a proof of concept, not a benchmark. The contribution is a reproducible intervention method for auditing trust in coding agents.

GitHub: https://github.com/aruneem-bhowmick/sieve
