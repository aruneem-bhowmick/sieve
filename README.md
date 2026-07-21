<p align="center">
  <img src="assets/sieve.svg" alt="Sieve logo" width="320" />
</p>

<h1 align="center">Sieve</h1>
<p align="center">Existing tools inspect an agent's reasoning. Sieve intervenes on it and measures whether the code actually follows.</p>

Sieve is a causal faithfulness auditor for coding agents. It captures a
structured rationale while an agent changes a task fixture, changes one stated
claim, constraint, or hypothesis, and compares the resulting patch and test
outcomes. The result is evidence about whether that rationale was necessary
for the observed software artifact—not a generic evaluation score or a claim
to reveal a model's private internal computation.

The [GitHub Pages report](https://aruneem-bhowmick.github.io/sieve/) is the
canonical public showcase. It is deterministic recorded audit evidence: the
deployed page is generated from the committed offline traces and scores, never
from a live model call.

## Clean setup

Sieve requires Python 3.11+ and Node.js 22+. From a clean repository checkout,
install the Python harness and the pinned dependencies used by the TypeScript
fixtures:

```powershell
python -m pip install -e ".[dev]"
npm ci
```

The repository's continuous checks use this same setup, invoke `python -m
sieve --help`, and run a recorded fixture without API credentials.

## One-command offline demo

After setup, run the complete deterministic audit and write its standalone
report:

```powershell
python -m sieve run-suite --runs-dir runs/release-audit --report-path report.html
```

This command never calls a model API or consumes API tokens. It writes five
recorded baselines, 15 single-intervention runs, and 15 score records beneath
`runs/release-audit/`, then creates `report.html`. Open that file locally to
inspect the patch-change/test-stability grid, per-task scores, and limitations.
Choose a new `--runs-dir` and report path for each invocation: Sieve refuses to
overwrite existing audit evidence.

For a smaller deterministic check of the first task, run:

GitHub Pages uses the same command in `.github/workflows/pages.yml` to publish
`site/index.html`. Once, set the repository’s **Settings → Pages → Build and
deployment → Source** to **GitHub Actions**. The generated page is a standalone
offline artifact and makes no network request when viewed.

For a smaller deterministic check of the first task, run:

```powershell
python -m sieve run --task SIEVE-T1 --runs-dir runs/first-task
```

## Recorded evidence and manual live checks

The default commands use reviewed recordings so the demo and automated checks
are repeatable. Recorded output demonstrates the intervention workflow and the
reporting path; it is not a fresh model invocation.

To manually exercise the direct OpenAI Responses API, provide an API key and
opt in with `--live`:

```powershell
$env:OPENAI_API_KEY = "..."
python -m sieve run-suite --live --runs-dir runs/live-audit --report-path live-report.html
```

Live runs can incur API charges and can vary between invocations. They are
manual smoke checks only: do not use them as a CI gate, and retain their output
separately from the recorded demo evidence.

## Interactive Vercel Hobby replay

Vercel Hobby hosts an interactive, replay-only version of the deterministic
5×3 evidence. It can locally edit, import, and export a five-task TypeScript
suite, but it never executes uploaded code, changes the recorded evidence, or
makes an API/model request. The full static report on GitHub Pages remains the
canonical deterministic artifact.

To deploy the Hobby page, import `aruneem-bhowmick/sieve` in Vercel, select
`main`, keep the repository defaults, and deploy. Do not configure Blob,
Redis, OpenAI, Sandbox, session, worker, or cron secrets/integrations. The
repository's `vercel.json` builds the Vite artifact into `public/`, and
`.vercelignore` excludes the retained `api/` source from the deployment.

After deployment, verify that recorded task/intervention replay works, the
editor can import and export a ZIP, the responsive layout remains usable, and
browser network activity contains no API or model requests. Live-audit source
is retained for a future supported isolated backend; it is not deployed on
Hobby. See [ADR 0002](docs/adr/0002-vercel-hobby-replay-only.md).

## Reading the result honestly

Sieve measures behavioral sensitivity to an edited structured rationale. A
stable patch and test result after an edit is evidence that the stated
rationale was not necessary for that output; it is not a mechanistic account
of how the model reached its decision. The structured rationale is deliberate
and bounded, and the included task set is an illustrative proof of concept,
not a general benchmark.

## Verification

Run the local quality gate with:

```powershell
ruff check .
black --check .
mypy --strict .
pytest -v
```

See [CHANGELOG.md](CHANGELOG.md) for the delivered core and deferred roadmap.
