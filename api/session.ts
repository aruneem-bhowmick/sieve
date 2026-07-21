import { createSession, passwordAccepted, sessionCookie } from "./_lib/session";

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const password = process.env.SIEVE_DEMO_PASSWORD;
  const secret = process.env.SIEVE_SESSION_SECRET;
  if (!password || !secret) return new Response("Live demo is not configured.", { status: 503 });
  const body = await request.json().catch(() => undefined) as { password?: unknown } | undefined;
  if (!body || typeof body.password !== "string" || !passwordAccepted(body.password, password)) return new Response("Unauthorized", { status: 401 });
  const { session, token } = createSession(secret);
  return Response.json({ csrf: session.csrf, expires_at: session.expiresAt }, { headers: { "set-cookie": sessionCookie(token), "cache-control": "no-store" } });
}
