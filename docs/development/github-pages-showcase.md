# GitHub Pages showcase and local replay

## Publish the canonical report

The GitHub Pages showcase is the canonical deterministic artifact. To enable it for a fork or a new repository, open **Settings → Pages → Build and deployment**, set **Source** to **GitHub Actions**, and save. Pushes to `main` then run [the Pages workflow](../../.github/workflows/pages.yml), which generates `site/index.html` from the recorded audit and publishes it as a standalone report with no runtime network request.

After the workflow completes, open the URL reported by GitHub Pages and confirm the report shows the causal-outcome grid, all 15 score rows, and Honest Limitations.

## Preview the interactive replay locally

After `npm ci`, build and serve the replay-only browser demo:

```powershell
npm run demo:build
npm run demo:preview
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173) in a browser. The local replay uses bundled recorded evidence: it does not execute imported tasks and makes no API or model request.
