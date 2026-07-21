import { defineSandboxProxy } from "@vercel/sandbox/proxy";
import { Redis } from "@upstash/redis";

export default defineSandboxProxy(async (request, meta) => {
  if (meta.host !== "api.openai.com" || request.method !== "POST" || !new URL(request.url).pathname.startsWith("/v1/responses")) return new Response("Forbidden", { status: 403 });
  const store = Redis.fromEnv();
  const jobId = await store.get<string>(`sieve:sandbox-job:${meta.sandboxName}`);
  if (!jobId) return new Response("Unknown sandbox", { status: 403 });
  const used = await store.incr(`sieve:requests:${jobId}`);
  if (used === 1) await store.expire(`sieve:requests:${jobId}`, 24 * 60 * 60);
  if (used > 130) return new Response("Demo model-request cap reached", { status: 429 });
  const headers = new Headers(request.headers);
  headers.set("authorization", `Bearer ${process.env.OPENAI_API_KEY ?? ""}`);
  headers.delete("vercel-sandbox-oidc-token");
  return fetch(`https://api.openai.com${new URL(request.url).pathname}${new URL(request.url).search}`, { method: "POST", headers, body: request.body });
});
