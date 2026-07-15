import { describe, expect, it } from "vitest";

import { formatUserLabel } from "../src/formatUserLabel";

describe("formatUserLabel", () => {
  it("keeps the original public export while normalizing a label", () => {
    expect(formatUserLabel("  Ada Lovelace  ")).toBe("Ada Lovelace");
  });
});
