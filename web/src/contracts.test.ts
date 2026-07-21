import { describe, expect, it } from "vitest";

import { validateLiveSuite, type DemoTask } from "./contracts";

function task(index: number): DemoTask {
  return {
    task_id: `SIEVE-T${index}`,
    files: {
      "task.md": "fix it",
      "intervention_constraints.json": "{}",
      "intervention_hypotheses.json": "{}",
      "src/fix.ts": "export {}",
      "tests/fix.test.ts": "export {}",
    },
  };
}

describe("validateLiveSuite", () => {
  it("accepts exactly five complete TypeScript tasks", () => {
    expect(validateLiveSuite([1, 2, 3, 4, 5].map(task))).toEqual([]);
  });

  it("rejects incomplete and non-full submissions", () => {
    const incomplete = task(1);
    delete incomplete.files["task.md"];
    expect(validateLiveSuite([incomplete])).toContain("A full live suite requires exactly five tasks.");
    expect(validateLiveSuite([incomplete]).join(" ")).toContain("missing task.md");
  });
});
