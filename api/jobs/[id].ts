import { readJob } from "../_lib/jobs";

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "GET") return new Response("Method not allowed", { status: 405 });
  const id = new URL(request.url).pathname.split("/").at(-1) ?? "";
  try { return Response.json(await readJob(request, id), { headers: { "cache-control": "no-store" } }); }
  catch (error) { return error instanceof Response ? error : new Response("Invalid job request", { status: 400 }); }
}
