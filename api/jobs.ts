import { createJob } from "./_lib/jobs";

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });
  try { return Response.json(await createJob(request, await request.json()), { status: 202, headers: { "cache-control": "no-store" } }); }
  catch (error) { return error instanceof Response ? error : new Response("Invalid live-suite request", { status: 400 }); }
}
