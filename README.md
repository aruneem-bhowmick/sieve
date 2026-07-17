<p align="center">
  <img src="assets/sieve.svg" alt="Sieve Logo" width="320" />
</p>

<h1 align="center">Sieve</h1>
<p align="center">Causal CoT Faithfulness Auditor for Codex (OpenAI Build Week).</p>

## Quick Start

Sieve requires Python 3.11+ and Node.js 22+. From a clean checkout, install the
Python harness and the pinned TypeScript fixture dependencies:

```powershell
python -m pip install -e ".[dev]"
npm ci
```

### Canonical offline demo

Run the deterministic recorded baseline for the first fixture:

```powershell
sieve run --task SIEVE-T1
```

The command writes `trace.json`, `final.diff`, and an isolated task workspace
under `runs/<run_id>/`; it uses no API tokens. It is verified from a clean
checkout in CI. If task tooling is missing, run `npm ci` from the repository
root. For a manual direct Responses API run, set `OPENAI_API_KEY` and add
`--live`; live runs are intentionally not part of CI.

Run the harness checks with:

```powershell
python -m pytest -v
python -m ruff check .
python -m black --check .
python -m mypy --strict .
```

See [CHANGELOG.md](CHANGELOG.md) for delivered capabilities and the planned
development roadmap. See the
[implementation guide](docs/workflow/SIEVE-IMPLEMENTATION-GUIDE.md) for the
ideator/executor workflow and reusable prompt templates.
