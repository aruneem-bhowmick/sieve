export type InterventionType = "INT-01" | "INT-02" | "INT-03";

export interface ReplayEntry {
  task_id: string;
  intervention_type: InterventionType;
  patch_divergence: number;
  outcome_stability: boolean;
  faithfulness_score: number;
  test_result: { passed: string[]; failed: string[] };
  intervention: {
    type: InterventionType | null;
    target_step_id: string | null;
    target_field: "claim" | "constraint" | "hypothesis" | null;
    original_value: string | null;
    replacement_value: string | null;
  };
  final_diff: string;
}

export interface DemoTask {
  task_id: string;
  files: Record<string, string>;
}

export interface ReplayBundle {
  version: number;
  tasks: DemoTask[];
  entries: ReplayEntry[];
  counts: Record<string, number>;
}

export const REQUIRED_TASK_FILES = [
  "task.md",
  "intervention_constraints.json",
  "intervention_hypotheses.json",
] as const;

export function validateLiveSuite(tasks: DemoTask[]): string[] {
  const errors: string[] = [];
  if (tasks.length !== 5) errors.push("A full live suite requires exactly five tasks.");
  const ids = new Set<string>();
  for (const task of tasks) {
    if (!/^SIEVE-[A-Za-z0-9-]+$/.test(task.task_id)) {
      errors.push(`${task.task_id}: task IDs must begin with SIEVE-.`);
    }
    if (ids.has(task.task_id)) errors.push(`${task.task_id}: task IDs must be unique.`);
    ids.add(task.task_id);
    for (const required of REQUIRED_TASK_FILES) {
      if (!(required in task.files)) errors.push(`${task.task_id}: missing ${required}.`);
    }
    if (!Object.keys(task.files).some((name) => name.startsWith("src/") && name.endsWith(".ts"))) {
      errors.push(`${task.task_id}: include at least one TypeScript source file.`);
    }
    if (!Object.keys(task.files).some((name) => name.startsWith("tests/") && name.endsWith(".test.ts"))) {
      errors.push(`${task.task_id}: include at least one Vitest test file.`);
    }
  }
  return errors;
}
