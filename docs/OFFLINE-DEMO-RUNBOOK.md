# Offline demo runbook

Use this runbook to produce and present Sieve's complete recorded audit when a
network connection or API credentials are unavailable. It runs the checked-in,
deterministic task recordings and creates new evidence for the presentation; it
does not copy, edit, or fabricate scores, traces, or report content.

## What this produces

The command below creates five baseline runs, 15 intervened runs, 15 score
records, and one self-contained HTML report. A successful full run prints:

```text
baselines=5
perturbed=15
scores=15
report=<absolute path to the generated report>
```

The report is a local file with inline styling and no external scripts,
stylesheets, or data requests. It remains viewable after disconnecting from the
network.

## One-time setup

Run these commands from a clean checkout of the repository root. They install
the pinned local tooling; do this before the presentation if package downloads
will not be available at the venue.

```powershell
git switch main
git pull --ff-only origin main
python --version
node --version
python -m pip install -e ".[dev]"
npm ci
```

Confirm that Python is 3.11 or newer and Node.js is 22 or newer. The recorded
fallback itself uses only the installed local Python package, checked-in task
recordings, and `node_modules`; it does not require `OPENAI_API_KEY`.

## Generate the fallback evidence

From the repository root, reserve the exact output directory below. The guard
prevents an accidental overwrite of an earlier presentation run.

```powershell
$demoRoot = Join-Path $PWD ".verification-runs\offline-demo"
if (Test-Path -LiteralPath $demoRoot) {
    throw "Offline demo output already exists at $demoRoot. Open its report or use Recovery before retrying."
}
New-Item -ItemType Directory -Path $demoRoot | Out-Null

$runDirectory = Join-Path $demoRoot "runs"
$reportPath = Join-Path $demoRoot "report.html"
python -m sieve run-suite --runs-dir $runDirectory --report-path $reportPath
```

Do not add `--live` to this command. The default backend is the deterministic
recorded backend, so this is the presenter-safe fallback and makes no model API
call.

## Verify and open the report

First, check the command summary: it must report 5 baselines, 15 perturbed
runs, 15 scores, and an absolute report path. Then run this local verification
before opening the file:

```powershell
$report = Get-Content -Raw -LiteralPath $reportPath
$rowCount = ([regex]::Matches($report, "<tr>")).Count
if (
    $report -notmatch 'id="two-by-two-grid"' -or
    $report -notmatch "<table>" -or
    $report -notmatch "Honest Limitations" -or
    $rowCount -ne 16
) {
    throw "Generated report is incomplete: expected the grid, 15-score table, and limitations."
}
if ($report -match '(?i)https?:|<script\b|<link\b') {
    throw "Generated report contains an external network reference; do not present it."
}
Start-Process -FilePath $reportPath
```

The 16 table rows are one header plus 15 recorded task/intervention scores.
In the opened report, confirm the four-cell causal-outcome grid, the table of
all 15 scores, and the **Honest Limitations** section are visible. Opening this
local file does not make network calls.

## Recovery

If setup fails because fixture tooling is missing, rerun `npm ci` from the
repository root and repeat the generation command. If the generator stops
after reserving the output directory, inspect the error, then remove only the
runbook-owned output and retry from **Generate the fallback evidence**:

```powershell
$demoRoot = Join-Path $PWD ".verification-runs\offline-demo"
if (Test-Path -LiteralPath $demoRoot) {
    Remove-Item -LiteralPath $demoRoot -Recurse -Force
}
```

Do not reuse a partially generated `runs` directory or overwrite a previous
report: each successful invocation must have its own output directory. If a
prior run completed, open its existing `report.html` rather than regenerating
it during the presentation.

## Optional live smoke test

Live API calls are optional manual smoke tests only. They are never required
for the recorded video, the offline fallback, or automated checks. Run a live
command only when credentials and network access are intentionally available,
using a separate, unused output location and `--live`; do not substitute it
for the recorded command above.
