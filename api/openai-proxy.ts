import { defineSandboxProxy } from "@vercel/sandbox/proxy";
import { Redis } from "@upstash/redis";

import { authorizedOpenAIRequest } from "./_lib/openai_proxy";

export default defineSandboxProxy(async (request, meta) => {
  if (meta.host !== "api.openai.com" || request.method !== "POST" || !new URL(request.url).pathname.startsWith("/v1/responses")) return new Response("Forbidden", { status: 403 });
  const store = Redis.fromEnv();
  const jobId = await store.get<string>(`sieve:sandbox-job:${meta.sandboxName}`);
  if (!jobId) return new Response("Unknown sandbox", { status: 403 });
  const used = await store.incr(`sieve:requests:${jobId}`);
  if (used === 1) await store.expire(`sieve:requests:${jobId}`, 24 * 60 * 60);
  if (used > 130) return new Response("Demo model-request cap reached", { status: 429 });
  return fetch(authorizedOpenAIRequest(request, process.env.OPENAI_API_KEY ?? ""));
});
