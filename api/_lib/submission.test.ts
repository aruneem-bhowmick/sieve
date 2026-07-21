import { describe, expect, it } from "vitest";

import { validateSubmission } from "./submission";

function task(index: number): { task_id: string; files: Record<string, string> } {
  return { task_id: `SIEVE-T${index}`, files: { "task.md": "Fix the task", "intervention_constraints.json": "{\"TSIEVE-T1-S001\":\"alternate\"}", "intervention_hypotheses.json": "{\"TSIEVE-T1-S001\":\"alternate\"}", "src/fix.ts": "export const fix = 1", "tests/fix.test.ts": "export {}", "package.json": "unsafe" } };
}

describe("live submission validation", () => {
  it("requires all five canonical tasks and strips user package manifests", () => {
    const submission = validateSubmission({ tasks: [1, 2, 3, 4, 5].map(task) });
    expect(submission.tasks).toHaveLength(5);
    expect(submission.tasks[0].files["package.json"]).toBeUndefined();
  });

  it("rejects path traversal and incomplete collections", () => {
    expect(() => validateSubmission({ tasks: [task(1)] })).toThrow("exactly five");
    const unsafe = task(1); unsafe.files["src/../outside.ts"] = "export {}";
    expect(() => validateSubmission({ tasks: [unsafe, task(2), task(3), task(4), task(5)] })).toThrow("unsupported file");
  });
});
