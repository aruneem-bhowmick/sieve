import { strFromU8, unzipSync, zipSync } from "fflate";

import replayBundle from "../static/replay.json";
import {
  type DemoTask,
  type ReplayBundle,
  type ReplayEntry,
  validateLiveSuite,
} from "./contracts";
import "./style.css";

const bundle = replayBundle as unknown as ReplayBundle;
const tasks = structuredClone(bundle.tasks);
let selectedTask = tasks[0]?.task_id ?? "";
let selectedIntervention = "INT-01";
let selectedFile = "task.md";
let csrf = "";

function escapeHtml(value: string): string {
  const node = document.createElement("span");
  node.textContent = value;
  return node.innerHTML;
}

function currentTask(): DemoTask {
  const task = tasks.find((candidate) => candidate.task_id === selectedTask);
  if (!task) throw new Error("Selected task is not available.");
  return task;
}

function selectedEntry(): ReplayEntry | undefined {
  return bundle.entries.find(
    (entry) => entry.task_id === selectedTask && entry.intervention_type === selectedIntervention,
  );
}

function evidence(entry: ReplayEntry | undefined): string {
  if (!entry) return "<p class=\"empty\">This recorded combination is unavailable.</p>";
  const broke = entry.test_result.failed.length > 0;
  return `<dl class="evidence"><div><dt>Patch divergence</dt><dd>${entry.patch_divergence.toFixed(3)}</dd></div><div><dt>Perturbed tests</dt><dd class="${broke ? "bad" : "good"}">${broke ? "Tests broke" : "Tests pass"}</dd></div><div><dt>Edited field</dt><dd>${escapeHtml(entry.intervention.target_field ?? "unknown")}</dd></div><div><dt>Outcome stability</dt><dd>${entry.outcome_stability ? "Stable" : "Changed"}</dd></div></dl><details><summary>Counterfactual evidence</summary><p><b>Original:</b> ${escapeHtml(entry.intervention.original_value || "(blank)")}</p><p><b>Replacement:</b> ${escapeHtml(entry.intervention.replacement_value || "(blank)")}</p><pre>${escapeHtml(entry.final_diff || "No final patch diff.")}</pre></details>`;
}

function render(): void {
  const task = currentTask();
  const files = Object.keys(task.files).sort();
  if (!files.includes(selectedFile)) selectedFile = files[0] ?? "task.md";
  document.querySelector<HTMLDivElement>("#app")!.innerHTML = `<main><header><a class="brand" href="#top" aria-label="Sieve interactive demo">SIEVE</a><span>Interactive causal audit</span><button id="login" class="quiet">Unlock live demo</button></header><section id="top" class="hero"><p class="eyebrow">Recorded replay · optional live sandbox</p><h1>Does an agent’s reasoning actually drive its code?</h1><p>Configure any recorded counterfactual now. Live mode audits your five-task TypeScript suite privately; it never changes the published benchmark evidence.</p></section><section class="grid"><article><p class="eyebrow">1. Replay the evidence</p><label>Task <select id="task">${tasks.map((candidate) => `<option ${candidate.task_id === selectedTask ? "selected" : ""}>${escapeHtml(candidate.task_id)}</option>`).join("")}</select></label><label>Intervention <select id="intervention">${["INT-01", "INT-02", "INT-03"].map((kind) => `<option ${kind === selectedIntervention ? "selected" : ""}>${kind}</option>`).join("")}</select></label>${evidence(selectedEntry())}</article><article><p class="eyebrow">2. Configure a full live suite</p><p class="small">Edit the five supplied fixtures, or import/export a ZIP. Live runs require all five tasks and all three interventions.</p><label>Fixture <select id="file">${files.map((file) => `<option value="${escapeHtml(file)}" ${file === selectedFile ? "selected" : ""}>${escapeHtml(file)}</option>`).join("")}</select></label><textarea id="editor" aria-label="${escapeHtml(selectedFile)}">${escapeHtml(task.files[selectedFile] ?? "")}</textarea><div class="actions"><button id="download">Export ZIP</button><label class="upload">Import ZIP <input id="upload" type="file" accept=".zip,application/zip" /></label><button id="start" class="primary">Validate & start live suite</button></div><p id="validation" role="status" class="small"></p></article></section><section class="limits"><p class="eyebrow">Live-demo limits</p><p>One active suite globally · one suite per browser session each UTC day · six suites globally each UTC day · 130 model requests · estimated maximum US$5/job · private artifacts deleted after 24 hours.</p><p>Custom-run results are user-supplied demonstration evidence, not benchmark evidence or a mechanistic claim about a model.</p></section><footer>Replay is bundled from recorded Sieve artifacts. No model request is made until you explicitly unlock and start a live suite.</footer></main>`;
  bind();
}

function bind(): void {
  document.querySelector<HTMLSelectElement>("#task")!.onchange = (event) => { selectedTask = (event.target as HTMLSelectElement).value; render(); };
  document.querySelector<HTMLSelectElement>("#intervention")!.onchange = (event) => { selectedIntervention = (event.target as HTMLSelectElement).value; render(); };
  document.querySelector<HTMLSelectElement>("#file")!.onchange = (event) => { selectedFile = (event.target as HTMLSelectElement).value; render(); };
  document.querySelector<HTMLTextAreaElement>("#editor")!.oninput = (event) => { currentTask().files[selectedFile] = (event.target as HTMLTextAreaElement).value; };
  document.querySelector<HTMLButtonElement>("#download")!.onclick = downloadSuite;
  document.querySelector<HTMLInputElement>("#upload")!.onchange = importSuite;
  document.querySelector<HTMLButtonElement>("#start")!.onclick = startSuite;
  document.querySelector<HTMLButtonElement>("#login")!.onclick = unlock;
}

function downloadSuite(): void {
  const archive: Record<string, Uint8Array> = {};
  for (const task of tasks) for (const [file, content] of Object.entries(task.files)) archive[`${task.task_id}/${file}`] = new TextEncoder().encode(content);
  const url = URL.createObjectURL(new Blob([zipSync(archive)], { type: "application/zip" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: "sieve-live-suite.zip" });
  link.click(); URL.revokeObjectURL(url);
}

async function importSuite(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const archive = unzipSync(new Uint8Array(await file.arrayBuffer()));
  const imported = new Map<string, DemoTask>();
  for (const [path, content] of Object.entries(archive)) {
    const [taskId, ...rest] = path.split("/");
    if (!taskId || rest.length === 0 || path.includes("..")) continue;
    const task = imported.get(taskId) ?? { task_id: taskId, files: {} };
    task.files[rest.join("/")] = strFromU8(content);
    imported.set(taskId, task);
  }
  tasks.splice(0, tasks.length, ...[...imported.values()].sort((left, right) => left.task_id.localeCompare(right.task_id)));
  selectedTask = tasks[0]?.task_id ?? ""; selectedFile = "task.md"; render();
}

async function startSuite(): Promise<void> {
  const errors = validateLiveSuite(tasks);
  const notice = document.querySelector<HTMLParagraphElement>("#validation")!;
  if (errors.length) { notice.textContent = errors.join(" "); notice.className = "bad small"; return; }
  if (!csrf) { notice.textContent = "Suite is valid. Unlock the live demo before starting it."; notice.className = "good small"; return; }
  const response = await fetch("/api/jobs", { method: "POST", headers: { "content-type": "application/json", "x-sieve-csrf": csrf }, body: JSON.stringify({ tasks }) });
  const result = await response.json().catch(() => ({})) as { id?: string };
  notice.textContent = response.ok ? `Live suite queued privately as ${result.id}.` : "The live suite could not be queued. Check the demo limits or configuration.";
  notice.className = response.ok ? "good small" : "bad small";
}

function unlock(): void {
  const password = window.prompt("Demo password");
  if (!password) return;
  fetch("/api/session", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ password }) })
    .then(async (response) => { if (!response.ok) throw new Error("Password was not accepted."); csrf = (await response.json() as { csrf: string }).csrf; document.querySelector<HTMLButtonElement>("#login")!.textContent = "Live demo unlocked"; })
    .catch((error: Error) => window.alert(error.message));
}

render();
