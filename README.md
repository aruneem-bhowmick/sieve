# Sieve

Causal CoT Faithfulness Auditor for Codex (OpenAI Build Week).

## Quick Start

Install the Python harness and TypeScript fixture dependencies:

```powershell
python -m pip install -e ".[dev]"
npm ci
```

Run the deterministic recorded baseline for the first fixture:

```powershell
sieve run --task SIEVE-T1
```

The command writes `trace.json`, `final.diff`, and an isolated task workspace
under `runs/<run_id>/`. It uses no API tokens. For a manual direct Responses
API run, set `OPENAI_API_KEY` and add `--live`; live runs are intentionally not
part of CI.

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
