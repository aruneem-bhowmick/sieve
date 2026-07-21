import { del, list } from "@vercel/blob";

const RETENTION_MS = 24 * 60 * 60 * 1000;

export default async function handler(request: Request): Promise<Response> {
  const secret = process.env.CRON_SECRET;
  if (!secret || request.headers.get("authorization") !== `Bearer ${secret}`) return new Response("Unauthorized", { status: 401 });
  const { blobs } = await list({ prefix: "sieve/" });
  const expired = blobs.filter((blob) => Date.now() - new Date(blob.uploadedAt).getTime() >= RETENTION_MS);
  if (expired.length) await del(expired.map((blob) => blob.url));
  return Response.json({ deleted: expired.length });
}
