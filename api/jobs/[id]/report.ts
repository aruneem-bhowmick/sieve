import { get } from "@vercel/blob";
import { Redis } from "@upstash/redis";

import { authenticated, type LiveJob } from "../../_lib/jobs";

export default async function handler(request: Request): Promise<Response> {
  const session = authenticated(request);
  const id = new URL(request.url).pathname.split("/").at(-2) ?? "";
  if (!session) return new Response("Unauthorized", { status: 401 });
  const job = await Redis.fromEnv().get<LiveJob>(`sieve:job:${id}`);
  if (!job || job.owner !== session.id || job.status !== "complete" || !job.report_path) return new Response("Not found", { status: 404 });
  const blob = await get(job.report_path, { access: "private" });
  if (!blob) return new Response("Not found", { status: 404 });
  return new Response(blob.stream as unknown as BodyInit, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}
