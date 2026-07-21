import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

const SESSION_SECONDS = 8 * 60 * 60;

export interface Session {
  id: string;
  csrf: string;
  expiresAt: number;
}

function encoded(value: string): string {
  return Buffer.from(value).toString("base64url");
}

function signature(value: string, secret: string): string {
  return createHmac("sha256", secret).update(value).digest("base64url");
}

/** Compare secrets without exposing where otherwise-equal values differ. */
export function secureEqual(candidate: string, expected: string): boolean {
  const candidateBytes = Buffer.from(candidate);
  const expectedBytes = Buffer.from(expected);
  return candidateBytes.length === expectedBytes.length && timingSafeEqual(candidateBytes, expectedBytes);
}

export function passwordAccepted(candidate: string, expected: string): boolean {
  return secureEqual(candidate, expected);
}

export function createSession(secret: string, now = Date.now()): { session: Session; token: string } {
  const session: Session = {
    id: randomBytes(18).toString("base64url"),
    csrf: randomBytes(18).toString("base64url"),
    expiresAt: now + SESSION_SECONDS * 1000,
  };
  const payload = encoded(JSON.stringify(session));
  return { session, token: `${payload}.${signature(payload, secret)}` };
}

export function readSession(token: string | undefined, secret: string, now = Date.now()): Session | undefined {
  if (!token) return undefined;
  const [payload, received] = token.split(".");
  if (!payload || !received) return undefined;
  const expected = signature(payload, secret);
  if (!secureEqual(received, expected)) return undefined;
  try {
    const session = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as Session;
    return typeof session.id === "string" && typeof session.csrf === "string" && session.expiresAt > now ? session : undefined;
  } catch {
    return undefined;
  }
}

export function sessionCookie(token: string): string {
  return `sieve_demo_session=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_SECONDS}`;
}

export function cookieValue(request: Request, name: string): string | undefined {
  return request.headers.get("cookie")?.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${name}=`))?.slice(name.length + 1);
}
