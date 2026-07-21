import { describe, expect, it } from "vitest";

import { createSession, passwordAccepted, readSession } from "./session";

describe("demo session", () => {
  it("accepts only the configured password with constant-time-compatible lengths", () => {
    expect(passwordAccepted("demo-password", "demo-password")).toBe(true);
    expect(passwordAccepted("wrong", "demo-password")).toBe(false);
  });

  it("signs an eight-hour session and rejects tampering or expiry", () => {
    const { session, token } = createSession("session-secret", 1_000);
    expect(readSession(token, "session-secret", 1_001)).toEqual(session);
    expect(readSession(`${token}x`, "session-secret", 1_001)).toBeUndefined();
    expect(readSession(token, "session-secret", session.expiresAt)).toBeUndefined();
  });
});
