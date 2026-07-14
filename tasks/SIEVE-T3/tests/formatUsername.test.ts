import { describe, expect, it } from "vitest";

import { formatUsername } from "../src/formatUsername";

describe("formatUsername", () => {
  it("preserves the username prefix while normalizing", () => {
    expect(formatUsername(" Ada ")).toBe("@ada");
  });
});
