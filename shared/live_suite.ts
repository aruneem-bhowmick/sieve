/** Browser- and server-safe shape checks for a live Sieve suite. */
export interface DemoTask {
  task_id: string;
  files: Record<string, string>;
}

export const REQUIRED_TASK_FILES = [
  "task.md",
  "intervention_constraints.json",
  "intervention_hypotheses.json",
] as const;

export const REQUIRED_TASK_IDS = ["SIEVE-T1", "SIEVE-T2", "SIEVE-T3", "SIEVE-T4", "SIEVE-T5"] as const;

export function validateLiveSuite(tasks: DemoTask[]): string[] {
  const errors: string[] = [];
  if (tasks.length !== REQUIRED_TASK_IDS.length) errors.push("A full live suite requires exactly five tasks.");
  const ids = new Set<string>();
  for (const task of tasks) {
    if (!/^SIEVE-[A-Za-z0-9-]+$/.test(task.task_id)) errors.push(`${task.task_id}: task IDs must begin with SIEVE-.`);
    if (ids.has(task.task_id)) errors.push(`${task.task_id}: task IDs must be unique.`);
    ids.add(task.task_id);
    for (const required of REQUIRED_TASK_FILES) if (!(required in task.files)) errors.push(`${task.task_id}: missing ${required}.`);
    if (!Object.keys(task.files).some((name) => name.startsWith("src/") && name.endsWith(".ts"))) errors.push(`${task.task_id}: include at least one TypeScript source file.`);
    if (!Object.keys(task.files).some((name) => name.startsWith("tests/") && name.endsWith(".test.ts"))) errors.push(`${task.task_id}: include at least one Vitest test file.`);
  }
  for (const id of REQUIRED_TASK_IDS) if (!ids.has(id)) errors.push(`A full suite must provide ${id}.`);
  return errors;
}
