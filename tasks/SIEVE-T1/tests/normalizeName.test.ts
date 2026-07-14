import { describe, expect, it } from "vitest";

import { normalizeName } from "../src/normalizeName";

describe("normalizeName", () => {
  it("returns an empty string when the API omits a name", () => {
    expect(normalizeName(undefined)).toBe("");
  });
});
