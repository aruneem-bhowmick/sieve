import { describe, expect, it } from "vitest";

import { parseTags } from "../src/parseTags";

describe("parseTags", () => {
  it("splits ordinary comma-separated tags", () => {
    expect(parseTags("alpha,beta")).toEqual(["alpha", "beta"]);
  });
});
