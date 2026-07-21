# ADR 0001 — Add an isolated interactive Vercel demo

**Status:** Accepted

## Context

The canonical Sieve deliverable is a reproducible, static `report.html`. Its
recorded evidence must remain usable offline and must not make model calls at
view time. The public demo now also needs to let a small, password-gated
audience configure the recorded evidence, edit or upload its own TypeScript
task suite, and request a live five-task by three-intervention audit. That
requires a server-side API key, durable job state, and execution of untrusted
code, which the existing static-report-only binding standard does not cover.

## Decision

Keep the existing static report and GitHub Pages deployment as the canonical
recorded-audit artifact. Add an optional Vercel deployment for an interactive
demo. Browser replay is bundled recorded data and makes no request until a
user explicitly starts a live run. Live runs require a password-created,
signed, HttpOnly session; run one full suite at a time globally; and permit at
most one full suite per session in a rolling 24-hour window. A full suite is
five baselines plus all fifteen INT-01/INT-02/INT-03 counterfactual runs.

The Vercel API persists only private, session-owned submissions and result
artifacts, deleting them after 24 hours. It uses a transactional job store for
the global lock and quota. Untrusted task code and agent-selected shell actions
run only in a Vercel Sandbox created from a trusted, dependency-pinned
snapshot. The Sandbox has no production secrets and no arbitrary egress. Its
only permitted model path is a server-side, job-scoped OpenAI proxy with a
strict request budget. The proxy owns `OPENAI_API_KEY`; the browser and
Sandbox never receive it. The initial demo limits a suite to 130 model
requests (eight baseline steps for each of five tasks and six resumed steps for
each of fifteen perturbations), one suite per session per UTC day, six suites
globally per UTC day, and a deployment-configured maximum estimated spend of
US$5 per job. The proxy rejects further requests before forwarding them. The
estimated-spend cap depends on deployment-supplied current token rates and is
not a billing guarantee.

Custom submissions are a validated collection of exactly five TypeScript task
fixtures. The in-browser editor starts from the shipped fixtures; ZIP import is
an equivalent transport. Each task contains `task.md`, `src/`, `tests/`, and
the reviewed alternative metadata required for INT-02 and INT-03. Package
manifests, lockfiles, binaries, symlinks, and dependency installation are not
accepted. The trusted snapshot supplies the pinned test tooling.

## Consequences

This is a separate demo service rather than an alteration to Sieve's three
audit layers or its §5 JSON contracts. The recorded report remains static,
deterministic, and deployable through GitHub Pages. The Vercel project needs
`SIEVE_DEMO_PASSWORD`, `SIEVE_SESSION_SECRET`, `OPENAI_API_KEY`, a private
Blob store, a transactional database connection, and
`SIEVE_SANDBOX_SNAPSHOT_ID`; missing live configuration disables live mode
without breaking browser replay. CI continues to use only recordings and
mocked API/proxy tests. A manual, allowlisted live smoke run is required after
deployment.

## Alternatives considered

Executing submitted code in a browser cannot reproduce the Python harness or
secure a model credential. Executing it directly in a Vercel Function would
expose application infrastructure and makes shell-command containment
insufficient. Giving an API key to the browser or Sandbox would expose a
billable credential. Those alternatives are rejected.
