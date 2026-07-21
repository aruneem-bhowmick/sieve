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
  return `<dl class="evidence"><div><dt>Patch divergence</dt><dd>${entry.patch_divergence.toFixed(3)}</dd></div><div><dt>Perturbed tests</dt><dd class="${broke ? "bad" : "good"}">${broke ? "Tests broke" : "Tests pass"}</dd></div><div><dt>Edited field</dt><dd>${escapeHtml(entry.intervention.target_field ?? "unknown")}</dd></div><div><dt>Outcome stability</dt><dd>${entry.outcome_stability ? "Stable" : "Changed"}</dd></div></dl><details><summary>Inspect the counterfactual evidence</summary><p><b>Original rationale</b> ${escapeHtml(entry.intervention.original_value || "(blank)")}</p><p><b>Edited rationale</b> ${escapeHtml(entry.intervention.replacement_value || "(blank)")}</p><pre>${escapeHtml(entry.final_diff || "No final patch diff.")}</pre></details>`;
}

function render(): void {
  const task = currentTask();
  const files = Object.keys(task.files).sort();
  const taskCount = tasks.length;
  const interventionCount = new Set(bundle.entries.map((entry) => entry.intervention_type)).size;
  if (!files.includes(selectedFile)) selectedFile = files[0] ?? "task.md";

  const taskOptions = tasks
    .map((candidate) => `<option ${candidate.task_id === selectedTask ? "selected" : ""}>${escapeHtml(candidate.task_id)}</option>`)
    .join("");
  const interventionOptions = ["INT-01", "INT-02", "INT-03"]
    .map((kind) => `<option ${kind === selectedIntervention ? "selected" : ""}>${kind}</option>`)
    .join("");
  const fileOptions = files
    .map((file) => `<option value="${escapeHtml(file)}" ${file === selectedFile ? "selected" : ""}>${escapeHtml(file)}</option>`)
    .join("");

  document.querySelector<HTMLDivElement>("#app")!.innerHTML = `
    <main>
      <header class="site-header">
        <a class="brand" href="#top" aria-label="Sieve interactive replay">SIEVE</a>
        <p>Recorded causal audit <span aria-hidden="true">/</span> replay edition</p>
      </header>

      <section id="top" class="hero">
        <div>
          <p class="eyebrow">Causal faithfulness, made inspectable</p>
          <h1>Evidence for whether stated reasoning changes the code.</h1>
          <p class="lede">Explore a completed counterfactual audit. Every result is recorded, deterministic, and ready to inspect—without running a model or executing submitted code.</p>
        </div>
        <aside class="audit-frame" aria-label="Recorded audit scope">
          <p class="eyebrow">Recorded audit</p>
          <dl>
            <div><dt>${taskCount}</dt><dd>tasks</dd></div>
            <div><dt>${interventionCount}</dt><dd>interventions</dd></div>
            <div><dt>${bundle.entries.length}</dt><dd>counterfactuals</dd></div>
          </dl>
          <p class="frame-note">Patch divergence is the primary signal. Test outcomes provide the practical context.</p>
        </aside>
      </section>

      <section class="method-strip" aria-label="Sieve method">
        <div><span>01</span><strong>Capture</strong><p>Record a structured rationale alongside each coding action.</p></div>
        <div><span>02</span><strong>Intervene</strong><p>Edit one claim, constraint, or hypothesis and resume the trace.</p></div>
        <div><span>03</span><strong>Compare</strong><p>Measure the patch and test outcome against the baseline.</p></div>
      </section>

      <section class="workbench">
        <article class="panel evidence-panel">
          <div class="panel-heading"><p class="eyebrow">Recorded evidence</p><h2>Inspect one counterfactual</h2></div>
          <div class="control-row">
            <label>Task <select id="task">${taskOptions}</select></label>
            <label>Intervention <select id="intervention">${interventionOptions}</select></label>
          </div>
          ${evidence(selectedEntry())}
        </article>

        <article class="panel editor-panel">
          <div class="panel-heading"><p class="eyebrow">Local suite preparation</p><h2>Prepare, then export</h2></div>
          <p class="small">Work with the supplied five-task suite locally. This hosted page never executes it, uploads it, or changes the recorded evidence.</p>
          <label>Fixture <select id="file">${fileOptions}</select></label>
          <textarea id="editor" aria-label="${escapeHtml(selectedFile)}">${escapeHtml(task.files[selectedFile] ?? "")}</textarea>
          <div class="actions"><button id="download">Export local ZIP</button><label class="upload">Import local ZIP <input id="upload" type="file" accept=".zip,application/zip" /></label></div>
          <p id="suite-notice" role="status" class="small">${escapeHtml(suiteNotice)}</p>
        </article>
      </section>

      <section class="notice">
        <p class="eyebrow">Replay-only guarantee</p>
        <p>This page serves bundled evidence only. It makes no API or model request, never runs submitted code, and does not transmit uploaded files.</p>
      </section>

      <footer><span>Sieve</span><span>Static recorded evidence · no runtime network or model calls</span></footer>
    </main>`;
  bind();
}

function bind(): void {
  document.querySelector<HTMLSelectElement>("#task")!.onchange = (event) => {
    selectedTask = (event.target as HTMLSelectElement).value;
    render();
  };
  document.querySelector<HTMLSelectElement>("#intervention")!.onchange = (event) => {
    selectedIntervention = (event.target as HTMLSelectElement).value;
    render();
  };
  document.querySelector<HTMLSelectElement>("#file")!.onchange = (event) => {
    selectedFile = (event.target as HTMLSelectElement).value;
    render();
  };
  document.querySelector<HTMLTextAreaElement>("#editor")!.oninput = (event) => {
    currentTask().files[selectedFile] = (event.target as HTMLTextAreaElement).value;
  };
  document.querySelector<HTMLButtonElement>("#download")!.onclick = downloadSuite;
  document.querySelector<HTMLInputElement>("#upload")!.onchange = importSuite;
}

function downloadSuite(): void {
  const archive: Record<string, Uint8Array> = {};
  for (const task of tasks) {
    for (const [file, content] of Object.entries(task.files)) {
      archive[`${task.task_id}/${file}`] = new TextEncoder().encode(content);
    }
  }
  const url = URL.createObjectURL(new Blob([zipSync(archive)], { type: "application/zip" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: "sieve-local-suite.zip" });
  link.click();
  URL.revokeObjectURL(url);
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
  selectedTask = tasks[0]?.task_id ?? "";
  selectedFile = "task.md";
  render();
}

render();
