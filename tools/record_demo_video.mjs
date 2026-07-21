/**
 * Render the visual (no-audio) master for the Sieve Build Week demo.
 *
 * The shots are recorded from the actual static audit, compiled local replay,
 * and checked-in source. A presenter adds the human voice track separately;
 * see docs/demo-video/README.md.
 */

import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, mkdir, copyFile, readdir, stat } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const videoRoot = path.join(root, "docs", "demo-video");
const reportPath = path.join(videoRoot, "artifacts", "sieve-audit.html");
const auditRoot = path.join(root, "runs", "demo-video-audit");
const outputRoot = path.join(videoRoot, "output");
const smokeRender = process.argv.includes("--smoke");
const visualMaster = path.join(outputRoot, smokeRender ? "sieve-demo-smoke.webm" : "sieve-demo-visual.webm");
const PORT = 4187;
const BASE = `http://127.0.0.1:${PORT}`;

const captionCss = `
  .sieve-video-caption {
    position: fixed; z-index: 10000; left: 34px; bottom: 28px; max-width: 760px;
    padding: 14px 18px; border: 1px solid #626262; border-left: 4px solid #f2f2f2;
    background: rgba(8,8,8,.92); box-shadow: 0 10px 30px rgba(0,0,0,.4);
    color: #f2f2f2; font: 600 17px/1.35 Inter, ui-sans-serif, system-ui, sans-serif;
  }
  .sieve-video-caption strong { display: block; margin-bottom: 3px; color: #bdbdbd;
    font-size: 11px; letter-spacing: .14em; text-transform: uppercase; }
`;

function html(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function shell(command, args) {
  const result = spawnSync(command, args, {
    cwd: root,
    encoding: "utf8",
    // Windows invokes npm through its .cmd shim; Node requires a shell for it.
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    throw new Error(`${command} failed:\n${result.stdout ?? ""}\n${result.stderr ?? result.error ?? ""}`);
  }
}

async function assertReadable(file, guidance) {
  try {
    await stat(file);
  } catch {
    throw new Error(guidance);
  }
}

async function startStaticServer() {
  const report = await readFile(reportPath, "utf8");
  const publicRoot = path.join(root, "public");
  const server = createServer(async (request, response) => {
    const pathname = new URL(request.url ?? "/", BASE).pathname;
    if (pathname === "/report.html") {
      response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      response.end(report);
      return;
    }
    const relative = pathname === "/" ? "index.html" : pathname.slice(1);
    const candidate = path.resolve(publicRoot, relative);
    if (!candidate.startsWith(publicRoot)) {
      response.writeHead(403).end();
      return;
    }
    try {
      const content = await readFile(candidate);
      const type = candidate.endsWith(".html")
        ? "text/html"
        : candidate.endsWith(".js")
          ? "text/javascript"
          : candidate.endsWith(".css")
            ? "text/css"
            : candidate.endsWith(".json")
              ? "application/json"
              : "application/octet-stream";
      response.writeHead(200, { "content-type": type });
      response.end(content);
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(PORT, "127.0.0.1", () => {
      server.off("error", reject);
      resolve();
    });
  });
  return server;
}

async function evidence(taskId, interventionType) {
  const entries = await Promise.all(
    (await readdir(auditRoot, { withFileTypes: true }))
      .filter((child) => child.isDirectory())
      .map(async (child) => JSON.parse(await readFile(path.join(auditRoot, child.name, "trace.json"), "utf8"))),
  );
  const trace = entries.find((entry) => entry.run_type === "perturbed" && entry.task_id === taskId && entry.intervention.type === interventionType);
  if (!trace) throw new Error(`Missing recorded evidence for ${taskId} ${interventionType}.`);
  const score = JSON.parse(await readFile(path.join(auditRoot, trace.run_id, "score.json"), "utf8"));
  return { trace, score };
}

function evidencePage(title, item, explanation) {
  const intervention = item.trace.intervention;
  const broke = item.trace.test_result.failed.length > 0;
  return `<!doctype html><meta charset="utf-8"><style>
    :root { color-scheme: dark; } * { box-sizing: border-box } body { margin:0; min-height:100vh; display:grid; place-items:center; background:#0b0b0b; color:#f2f2f2; font-family:Inter,system-ui,sans-serif } main { width:min(1080px,calc(100% - 80px)); } .brand { color:#aaa; font-size:13px; font-weight:800; letter-spacing:.18em } h1 { margin:18px 0 8px; font-size:52px; letter-spacing:-.05em; line-height:1 } .lede { color:#aaa; font-size:19px; max-width:760px } .card { margin-top:36px; padding:28px; border:1px solid #3a3a3a; background:#141414 } .grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1px; background:#3a3a3a; margin:24px 0 } .grid div { min-height:106px; padding:18px; background:#101010 } dt { color:#999; font-size:11px; font-weight:800; letter-spacing:.1em; text-transform:uppercase } dd { margin:10px 0 0; font-size:23px; font-weight:750 } .swap { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:22px } .swap div { padding:17px; border-left:3px solid #eee; background:#0d0d0d } .swap strong { display:block; margin-bottom:8px; color:#999; font-size:11px; letter-spacing:.1em; text-transform:uppercase } .note { color:#cfcfcf; font-size:18px; line-height:1.5 } .bad { text-decoration:underline; text-underline-offset:4px; text-decoration-color:#777 }
  </style><main><div class="brand">SIEVE / RECORDED AUDIT EVIDENCE</div><h1>${html(title)}</h1><p class="lede">${html(explanation)}</p><section class="card"><div class="grid"><div><dt>Edited field</dt><dd>${html(intervention.target_field)}</dd></div><div><dt>Patch divergence</dt><dd>${item.score.patch_divergence.toFixed(3)}</dd></div><div><dt>Perturbed tests</dt><dd class="${broke ? "bad" : ""}">${broke ? "Tests broke" : "Tests pass"}</dd></div><div><dt>Outcome stability</dt><dd>${item.score.outcome_stability ? "Stable" : "Changed"}</dd></div></div><div class="swap"><div><strong>Original rationale</strong>${html(intervention.original_value || "(blank)")}</div><div><strong>Edited rationale</strong>${html(intervention.replacement_value || "(blank)")}</div></div><p class="note">${html(broke ? "The original acceptance test is listed as failed in the recorded perturbed trace." : "The recorded perturbed trace has the same passing and failing test sets as the baseline.")}</p></section></main>`;
}

function terminalPage() {
  return `<!doctype html><meta charset="utf-8"><style>
    body { margin:0; min-height:100vh; display:grid; place-items:center; background:#080808; color:#e8e8e8; font:22px/1.65 ui-monospace,Consolas,monospace } main { width:min(1080px,calc(100% - 100px)); padding:36px; border:1px solid #363636; background:#101010; box-shadow:0 25px 70px #000 } .bar { color:#999; font:700 13px system-ui,sans-serif; letter-spacing:.12em; text-transform:uppercase; margin-bottom:24px } .prompt { color:#bbb } .command { color:#fff } .out { margin-top:24px; color:#d9d9d9 } .ok { color:#fff; font-weight:800 } .note { color:#aaa; font:17px/1.5 system-ui,sans-serif; margin-top:26px; padding-top:22px; border-top:1px solid #333 }
  </style><main><div class="bar">PowerShell · Sieve recorded audit</div><div><span class="prompt">PS Sieve&gt; </span><span class="command">python -m sieve run-suite --runs-dir runs/demo-video-audit --report-path docs/demo-video/artifacts/sieve-audit.html</span></div><div class="out">baselines=<span class="ok">5</span><br>perturbed=<span class="ok">15</span><br>scores=<span class="ok">15</span><br>report=docs/demo-video/artifacts/sieve-audit.html</div><p class="note">Recorded backend · offline evidence · no API key or model request in this demo run</p></main>`;
}

function sourcePage(agentSource, cliSource) {
  const agentLines = agentSource.split("\n").slice(65, 122).join("\n");
  const cliLines = cliSource.split("\n").slice(20, 49).join("\n");
  return `<!doctype html><meta charset="utf-8"><style>
    :root{color-scheme:dark}body{margin:0;background:#0b0b0b;color:#ddd;font:15px/1.42 ui-monospace,Consolas,monospace}main{width:calc(100% - 72px);margin:34px 36px}.bar{display:flex;justify-content:space-between;padding:13px 16px;border:1px solid #353535;background:#151515;color:#aaa;font:700 12px system-ui,sans-serif;letter-spacing:.1em}.columns{display:grid;grid-template-columns:1.28fr .72fr;gap:12px;margin-top:12px}.file{overflow:hidden;border:1px solid #353535;background:#101010}.file h2{margin:0;padding:12px 15px;border-bottom:1px solid #353535;color:#f1f1f1;font:700 13px system-ui,sans-serif}.file pre{margin:0;padding:15px;white-space:pre-wrap}.highlight{color:#fff;background:#252525;display:block;margin:0 -15px;padding:0 15px;border-left:3px solid #eee}
  </style><main><div class="bar"><span>SIEVE / DIRECT CODING-AGENT INTEGRATION</span><span>LOCAL SOURCE VIEW</span></div><div class="columns"><section class="file"><h2>src/sieve/agent.py · response_tools()</h2><pre>${html(agentLines).replace("function", "<span class=\"highlight\">function</span>")}</pre></section><section class="file"><h2>src/sieve/cli.py · live mode</h2><pre>${html(cliLines)}</pre></section></div></main>`;
}

function endCard(logo) {
  return `<!doctype html><meta charset="utf-8"><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0b0b;color:#f3f3f3;font-family:Inter,system-ui,sans-serif}main{text-align:center}svg{width:140px;filter:grayscale(1) brightness(2.2)}h1{margin:24px 0 12px;font-size:82px;letter-spacing:.14em}p{color:#aaa;font-size:22px}.tag{margin-top:38px;color:#ddd;font-weight:800;letter-spacing:.13em;text-transform:uppercase;font-size:14px}.url{margin-top:14px;color:#aaa;font:16px ui-monospace,Consolas,monospace}</style><main>${logo}<h1>SIEVE</h1><p>Turn agent reasoning into something developers can test.</p><div class="tag">OpenAI Build Week · Developer Tools</div><div class="url">github.com/aruneem-bhowmick/sieve</div></main>`;
}

async function addCaption(page, label, body) {
  await page.addStyleTag({ content: captionCss });
  await page.evaluate(({ label, body }) => {
    document.querySelectorAll(".sieve-video-caption").forEach((caption) => caption.remove());
    const caption = document.createElement("aside");
    caption.className = "sieve-video-caption";
    caption.innerHTML = `<strong>${label}</strong>${body}`;
    document.body.append(caption);
  }, { label, body });
}

async function main() {
  await assertReadable(reportPath, "Missing generated report. Run the recorded audit command in docs/demo-video/README.md first.");
  await assertReadable(auditRoot, "Missing demo-video-audit traces. Run the recorded audit command in docs/demo-video/README.md first.");
  await mkdir(outputRoot, { recursive: true });
  try { await stat(visualMaster); throw new Error(`Refusing to overwrite ${visualMaster}. Move or rename it before rendering again.`); } catch (error) { if (error.code !== "ENOENT") throw error; }

  if (!process.argv.includes("--skip-build")) {
    shell(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "demo:build"]);
  }
  const recordingDirectory = path.join(outputRoot, `recording-${new Date().toISOString().replaceAll(":", "-").replaceAll(".", "-")}`);
  await mkdir(recordingDirectory);
  const server = await startStaticServer();
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: recordingDirectory, size: { width: 1280, height: 720 } } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.setDefaultNavigationTimeout(10000);
  const video = page.video();
  const t3 = await evidence("SIEVE-T3", "INT-02");
  const t1 = await evidence("SIEVE-T1", "INT-01");
  const agentSource = await readFile(path.join(root, "src", "sieve", "agent.py"), "utf8");
  const cliSource = await readFile(path.join(root, "src", "sieve", "cli.py"), "utf8");
  const logo = await readFile(path.join(root, "assets", "sieve.svg"), "utf8");

  async function capture(name, seconds, setup) {
    process.stdout.write(`Starting ${name}\n`);
    await setup(page);
    const effectiveSeconds = smokeRender ? 1 : seconds;
    await page.waitForTimeout(effectiveSeconds * 1000);
    process.stdout.write(`Recorded ${name} (${effectiveSeconds}s)\n`);
  }

  try {
    await capture("hero", 10, async (page) => { await page.goto(`${BASE}/report.html`, { waitUntil: "load" }); await addCaption(page, "Causal faithfulness auditor", "Does an agent’s reasoning actually drive its code?"); });
    await capture("method", 14, async (page) => { await page.goto(`${BASE}/report.html#method`, { waitUntil: "load" }); await page.locator("#method").scrollIntoViewIfNeeded(); await addCaption(page, "Structured rationale", "Capture → Intervene → Compare"); });
    await capture("agent-integration", 18, async (page) => { await page.setContent(sourcePage(agentSource, cliSource)); await addCaption(page, "Codex / GPT-5.6 integration", "Direct Responses API · strict emit_step schema · manual --live mode"); });
    await capture("recorded-suite", 15, async (page) => { await page.setContent(terminalPage()); await addCaption(page, "Deterministic recorded audit", "5 baselines · 15 interventions · 15 scores · no API request"); });
    await capture("constraint-sensitive", 20, async (page) => { await page.setContent(evidencePage("SIEVE-T3 / INT-02", t3, "One stated constraint is swapped; this recorded counterfactual follows the replacement constraint.")); await addCaption(page, "Patch divergence", "Constraint-sensitive: 0.025 divergence · original acceptance test broke"); });
    await capture("claim-insensitive", 19, async (page) => { await page.setContent(evidencePage("SIEVE-T1 / INT-01", t1, "One stated claim is deleted; this recorded counterfactual keeps the working result.")); await addCaption(page, "Test stability", "Claim-insensitive: 0.000 divergence · tests remain stable"); });
    await capture("grid-and-matrix", 17, async (page) => { await page.goto(`${BASE}/report.html?shot=grid#two-by-two-grid`, { waitUntil: "load" }); await page.locator("#two-by-two-grid").scrollIntoViewIfNeeded(); await addCaption(page, "Aggregate evidence", "AST-level patch divergence + test stability across all 15 interventions"); await page.waitForTimeout(8000); await page.locator("#result-matrix").scrollIntoViewIfNeeded(); });
    await capture("interactive-replay", 16, async (page) => { await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" }); await addCaption(page, "Replay-only local demo", "Inspect recorded evidence · edit a local fixture · export a five-task ZIP"); await page.selectOption("#task", "SIEVE-T3"); await page.selectOption("#intervention", "INT-02"); await page.locator("summary").click(); await page.locator("#editor").fill("// Locally prepared only; this replay never executes code.\n" + await page.locator("#editor").inputValue()); await page.waitForTimeout(6000); await page.locator("#download").click(); });
    await capture("limitations", 15, async (page) => { await page.goto(`${BASE}/report.html#honest-limitations`, { waitUntil: "load" }); await page.locator("#honest-limitations").scrollIntoViewIfNeeded(); await addCaption(page, "Honest limitations", "Behavioral sensitivity—not private internal reasoning · five tasks are a proof of concept"); });
    await capture("end-card", 6, async (page) => { await page.setContent(endCard(logo)); await addCaption(page, "Developer Tools", "Sieve: reasoning developers can test"); });
  } finally {
    await context.close();
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }

  await copyFile(await video.path(), visualMaster);
  process.stdout.write(`Visual master: ${visualMaster}\n`);
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
