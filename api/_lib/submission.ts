import { type DemoTask, REQUIRED_TASK_FILES, validateLiveSuite } from "../../shared/live_suite";

export type SubmittedTask = DemoTask;

const MAX_FILES = 100;
const MAX_BYTES = 256 * 1024;

export function validateSubmission(value: unknown): { tasks: SubmittedTask[] } {
  if (!value || typeof value !== "object" || !Array.isArray((value as { tasks?: unknown }).tasks)) throw new Error("A task collection is required.");
  const tasks = (value as { tasks: unknown[] }).tasks;
  const ids = new Set<string>(); let files = 0; let bytes = 0;
  const validated = tasks.map((candidate) => {
    if (!candidate || typeof candidate !== "object") throw new Error("Each task must be an object.");
    const { task_id: taskId, files: taskFiles } = candidate as SubmittedTask;
    if (typeof taskId !== "string" || ids.has(taskId)) throw new Error("Task IDs must be unique SIEVE-* identifiers.");
    ids.add(taskId);
    if (!taskFiles || typeof taskFiles !== "object") throw new Error(`${taskId}: files are required.`);
    const normalized: Record<string, string> = {};
    for (const [path, content] of Object.entries(taskFiles)) {
      if (!allowedPath(path) || typeof content !== "string") throw new Error(`${taskId}: unsupported file ${path}.`);
      files += 1; bytes += Buffer.byteLength(content); normalized[path] = content;
    }
    for (const metadata of REQUIRED_TASK_FILES.slice(1)) try { if (!Object.keys(JSON.parse(normalized[metadata] ?? "")).length) throw new Error(); } catch { throw new Error(`${taskId}: ${metadata} must contain reviewed replacements.`); }
    delete normalized["package.json"];
    return { task_id: taskId, files: normalized };
  });
  const shapeErrors = validateLiveSuite(validated);
  if (shapeErrors.length) throw new Error(shapeErrors.join(" "));
  if (files > MAX_FILES || bytes > MAX_BYTES) throw new Error("The submitted suite exceeds demo file or size limits.");
  return { tasks: validated };
}

function allowedPath(path: string): boolean {
  if (path.includes("..") || path.startsWith("/") || path.includes("\\")) return false;
  return path === "task.md" || path === "package.json" || path === "intervention_constraints.json" || path === "intervention_hypotheses.json" || /^(src|tests)\/[A-Za-z0-9._/-]+\.tsx?$/.test(path);
}
