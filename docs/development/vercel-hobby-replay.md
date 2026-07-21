# Vercel Hobby replay deployment

The Vercel Hobby deployment is a static, replay-only companion to the canonical [GitHub Pages report](https://aruneem-bhowmick.github.io/sieve/). It lets visitors inspect the recorded 5×3 evidence and prepare, import, or export a five-task TypeScript suite locally. It never executes submitted code, changes recorded evidence, or makes an API or model request.

## Deploy

1. Import `aruneem-bhowmick/sieve` into Vercel.
2. Select the `main` branch and keep the repository defaults.
3. Do not configure Blob, Redis, OpenAI, Sandbox, session, worker, or cron secrets/integrations.

`vercel.json` builds the Vite artifact into `public/`; `.vercelignore` excludes the retained `api/` source. The build creates an isolated temporary virtual environment for replay export, so it does not alter Vercel's managed Python installation.

## Verify

Confirm that task/intervention replay works, ZIP import and export works, and the layout is usable at narrow widths. Browser network activity must contain no API or model request. Live-audit source is retained for a future isolated backend and is not deployed on Hobby; see [ADR 0002](../adr/0002-vercel-hobby-replay-only.md).
