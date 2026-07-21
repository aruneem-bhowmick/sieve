import { strFromU8, unzipSync, zipSync } from "fflate";

import replayBundle from "../static/replay.json";
import {
  type DemoTask,
  type ReplayBundle,
  type ReplayEntry,
} from "./contracts";
import "./style.css";

const bundle = replayBundle as unknown as ReplayBundle;
const tasks = structuredClone(bundle.tasks);
let selectedTask = tasks[0]?.task_id ?? "";
let selectedIntervention = "INT-01";
let selectedFile = "task.md";
let suiteNotice = "";

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
  document.querySelector<HTMLDivElement>("#app")!.innerHTML = `<main><header><a class="brand" href="#top" aria-label="Sieve interactive replay">SIEVE</a><span>Interactive causal audit replay</span></header><section id="top" class="hero"><p class="eyebrow">Recorded evidence · local suite preparation</p><h1>Does an agent’s reasoning actually drive its code?</h1><p>Explore the recorded five-task, three-intervention evidence, then prepare a local five-task TypeScript suite for a future audit. Your edits never change the recorded evidence and are not executed on this hosted page.</p></section><section class="grid"><article><p class="eyebrow">1. Replay the evidence</p><label>Task <select id="task">${tasks.map((candidate) => `<option ${candidate.task_id === selectedTask ? "selected" : ""}>${escapeHtml(candidate.task_id)}</option>`).join("")}</select></label><label>Intervention <select id="intervention">${["INT-01", "INT-02", "INT-03"].map((kind) => `<option ${kind === selectedIntervention ? "selected" : ""}>${kind}</option>`).join("")}</select></label>${evidence(selectedEntry())}</article><article><p class="eyebrow">2. Prepare a local five-task suite</p><p class="small">Edit the supplied fixtures or import/export a ZIP. Everything stays in this browser until you export it; the hosted replay never runs submitted code.</p><label>Fixture <select id="file">${files.map((file) => `<option value="${escapeHtml(file)}" ${file === selectedFile ? "selected" : ""}>${escapeHtml(file)}</option>`).join("")}</select></label><textarea id="editor" aria-label="${escapeHtml(selectedFile)}">${escapeHtml(task.files[selectedFile] ?? "")}</textarea><div class="actions"><button id="download">Export ZIP</button><label class="upload">Import ZIP <input id="upload" type="file" accept=".zip,application/zip" /></label></div><p id="suite-notice" role="status" class="small">${escapeHtml(suiteNotice)}</p></article></section><section class="notice"><p class="eyebrow">Replay-only guarantee</p><p>This Vercel Hobby page makes no API or model request. It only displays bundled recorded evidence and processes ZIP files locally in your browser.</p></section><footer>Recorded replay is bundled from Sieve artifacts. This hosted page never executes uploaded code, changes the evidence, or contacts an API or model.</footer></main>`;
  bind();
}

function bind(): void {
  document.querySelector<HTMLSelectElement>("#task")!.onchange = (event) => { selectedTask = (event.target as HTMLSelectElement).value; render(); };
  document.querySelector<HTMLSelectElement>("#intervention")!.onchange = (event) => { selectedIntervention = (event.target as HTMLSelectElement).value; render(); };
  document.querySelector<HTMLSelectElement>("#file")!.onchange = (event) => { selectedFile = (event.target as HTMLSelectElement).value; render(); };
  document.querySelector<HTMLTextAreaElement>("#editor")!.oninput = (event) => { currentTask().files[selectedFile] = (event.target as HTMLTextAreaElement).value; };
  document.querySelector<HTMLButtonElement>("#download")!.onclick = downloadSuite;
  document.querySelector<HTMLInputElement>("#upload")!.onchange = importSuite;
}

function downloadSuite(): void {
  const archive: Record<string, Uint8Array> = {};
  for (const task of tasks) for (const [file, content] of Object.entries(task.files)) archive[`${task.task_id}/${file}`] = new TextEncoder().encode(content);
  const url = URL.createObjectURL(new Blob([zipSync(archive)], { type: "application/zip" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: "sieve-local-suite.zip" });
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
    task.files[rest.join("/")] = strFromU8(content as Uint8Array);
    imported.set(taskId, task);
  }
  if (imported.size !== 5) {
    suiteNotice = "Import a ZIP containing exactly five task folders; the current local suite was not changed.";
    render();
    return;
  }
  tasks.splice(0, tasks.length, ...[...imported.values()].sort((left, right) => left.task_id.localeCompare(right.task_id)));
  suiteNotice = "Imported locally. Review or export this suite; it is not executed by this page.";
  selectedTask = tasks[0]?.task_id ?? ""; selectedFile = "task.md"; render();
}

render();
