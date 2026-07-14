# Sieve

Causal CoT Faithfulness Auditor for Codex (OpenAI Build Week).

## Phase 0

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
