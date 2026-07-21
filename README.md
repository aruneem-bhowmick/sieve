<p align="center">
  <img src="assets/sieve.svg" alt="Sieve logo" width="320" />
</p>

# Sieve

Sieve tests whether a coding agent's stated rationale is actually load-bearing: edit one reason, then measure whether the code or tests change.

[Watch the demo video](https://www.youtube.com/watch?v=ZrjJlJ-EzrM) · [Read the Devpost submission](https://devpost.com/software/sieve-es0x8f) · [Explore the recorded report](https://aruneem-bhowmick.github.io/sieve/)

## Capture → Intervene → Compare

Sieve captures each agent step as a structured claim, constraint, and hypothesis. It changes one field while keeping the prior trajectory fixed, then compares the resulting TypeScript patch structurally and checks whether the test outcomes stayed the same. The result is behavioral evidence—not a claim to reveal a model's private reasoning.

The public report is deterministic recorded evidence: it is generated from reviewed traces and scores, makes no model request when viewed, and can be reproduced locally without an API key. The included five-task suite covers bug fixes, constrained refactors, and test generation across three intervention types.

## Reproduce the recorded audit

Requires Python 3.11+ and Node.js 22+.

```powershell
python -m pip install -e ".[dev]"
npm ci
python -m sieve run-suite --runs-dir runs/release-audit --report-path report.html
```

This command never calls a model API or consumes API tokens. It writes five baselines, 15 single-intervention runs, 15 score records, and a standalone `report.html`. Choose a new output path for each run; Sieve refuses to overwrite evidence.

## Limits

A stable patch and test result after an edit indicates that the stated field was not necessary for that observed output. It does not explain a model's internal computation. The structured rationale is deliberately bounded, and five tasks are a proof of concept rather than a benchmark.

## Documentation

- [Judge guide and evidence](docs/README.md)
- [Methodology](docs/build-week/methodology.md)
- [Presenter-safe offline runbook](docs/build-week/offline-demo-runbook.md)
- [Development documentation](docs/development/README.md)

See [CHANGELOG.md](CHANGELOG.md) for shipped work and the deferred roadmap.
