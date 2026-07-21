# Narration — 2:50

Read this at a natural, unhurried pace. It is intentionally written as a
single voice, with no music.

**0:00–0:12**

Coding agents explain why they make a change. But how do we know that
explanation actually drove the code? Sieve intervenes on the reasoning and
measures what changes.

**0:12–0:28**

Sieve is a causal faithfulness auditor for coding agents. It captures a
structured rationale, edits one claim, constraint, or hypothesis mid-run,
resumes the task, and compares the resulting patch and tests.

**0:28–0:48**

I use Codex and GPT-5.6 as the coding agent under audit through the direct
Responses API backend. Before every tool action, Sieve requires a strict
structured step: claim, constraint, hypothesis, planned action, and success
criterion. That makes a precise counterfactual intervention possible instead
of merely judging prose after the fact.

**0:48–1:05**

For a reproducible demo, I run the recorded five-task audit. It produces five
baselines, fifteen single-field interventions, fifteen score records, and a
standalone report—without an API key or a live model request during this
recording.

**1:05–1:27**

Here is a constraint-sensitive result. Sieve changes only the stated
requirement from preserving an at-sign prefix to preserving a hash prefix. The
patch follows that replacement constraint, and the original acceptance test
breaks. That is evidence this constraint was load-bearing for this output.

**1:27–1:48**

Now the opposite case. Sieve deletes the claim that an optional name may be
absent. The final patch is unchanged and the tests still pass. This specific
claim was not necessary for that output.

**1:48–2:07**

The headline view aggregates every result by patch change and test stability.
Sieve scores software artifacts with AST-level patch divergence and test
outcomes—not text similarity—so a developer can inspect both faithful and
decorative rationales across the suite.

**2:07–2:25**

The polished replay lets a reviewer inspect the recorded five-by-three matrix
and locally prepare or export a five-task suite. It is intentionally
replay-only: it does not execute uploaded code, change evidence, or make an
API or model request.

**2:25–2:42**

Sieve is not claiming to reveal a model’s private internal reasoning. It
measures behavioral sensitivity to a declared structured rationale. Five tasks
are a proof of concept; the contribution is a reproducible intervention
harness for evaluating coding-agent trust.

**2:42–2:47.6**

Sieve turns agent reasoning from something developers merely read into
something they can test.
