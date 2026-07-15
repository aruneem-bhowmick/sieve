import { describe, expect, it } from "vitest";

import { clampPage } from "../src/clampPage";

describe("clampPage", () => {
  it("clamps a zero page to the first one-based page", () => {
    expect(clampPage(0, 5)).toBe(1);
  });
});
