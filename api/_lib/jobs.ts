import { randomUUID } from "node:crypto";

import { put } from "@vercel/blob";
import { waitUntil } from "@vercel/functions";
import { Redis } from "@upstash/redis";

import { cookieValue, readSession, secureEqual } from "./session";
import { type SubmittedTask, validateSubmission } from "./submission";

const DAY_SECONDS = 24 * 60 * 60;
const RESULT_SECONDS = DAY_SECONDS;

export type LiveJobStatus = "queued" | "running" | "complete" | "failed";

export interface LiveJob {
  id: string;
  owner: string;
  status: LiveJobStatus;
  createdAt: number;
  expiresAt: number;
  report_path?: string;
  error?: string;
}

function redis(): Redis { return Redis.fromEnv(); }

function configured(): boolean {
  return Boolean(process.env.SIEVE_SANDBOX_SNAPSHOT_ID && process.env.OPENAI_API_KEY && process.env.SIEVE_TURN_PROXY_URL && process.env.UPSTASH_REDIS_REST_URL && process.env.BLOB_READ_WRITE_TOKEN);
}

export function authenticated(request: Request): { id: string; csrf: string } | undefined {
  const secret = process.env.SIEVE_SESSION_SECRET;
  return secret ? readSession(cookieValue(request, "sieve_demo_session"), secret) : undefined;
}

export async function createJob(request: Request, body: unknown): Promise<LiveJob> {
  const session = authenticated(request);
  if (!session) throw new Response("Unauthorized", { status: 401 });
  if (!secureEqual(request.headers.get("x-sieve-csrf") ?? "", session.csrf)) throw new Response("CSRF validation failed", { status: 403 });
  if (!configured()) throw new Response("Live demo is not configured.", { status: 503 });
  const submission = validateSubmission(body);
  const store = redis(); const today = new Date().toISOString().slice(0, 10);
  const globalCount = Number(await store.get<number>(`sieve:day:${today}`) ?? 0);
  const ownerCount = Number(await store.get<number>(`sieve:day:${today}:${session.id}`) ?? 0);
  if (globalCount >= 6 || ownerCount >= 1) throw new Response("The demo quota has been reached.", { status: 429 });
  const id = randomUUID();
  const lock = await store.set("sieve:active", id, { nx: true, ex: 15 * 60 });
  if (lock !== "OK") throw new Response("Another live suite is already running.", { status: 409 });
  const job: LiveJob = { id, owner: session.id, status: "queued", createdAt: Date.now(), expiresAt: Date.now() + RESULT_SECONDS * 1000 };
  await Promise.all([
    store.set(`sieve:job:${id}`, job, { ex: RESULT_SECONDS }),
    store.incr(`sieve:day:${today}`), store.expire(`sieve:day:${today}`, DAY_SECONDS),
    store.incr(`sieve:day:${today}:${session.id}`), store.expire(`sieve:day:${today}:${session.id}`, DAY_SECONDS),
    put(`sieve/${id}/submission.json`, JSON.stringify(submission), { access: "private", addRandomSuffix: false }),
  ]);
  waitUntil(runQueuedSuite(store, job, submission));
  return job;
}

async function runQueuedSuite(store: Redis, job: LiveJob, submission: { tasks: SubmittedTask[] }): Promise<void> {
  // The worker is intentionally split into a separately deployed, OIDC-authenticated
  // turn proxy. It is started only after the atomic lock and private submission write.
  // Deployment operators supply SIEVE_LIVE_WORKER_URL; absent configuration remains a
  // safe unavailable state instead of running arbitrary code in this function.
  const worker = process.env.SIEVE_LIVE_WORKER_URL;
  try {
    if (!worker) throw new Error("SIEVE_LIVE_WORKER_URL is not configured");
    await store.set(`sieve:job:${job.id}`, { ...job, status: "running" }, { ex: RESULT_SECONDS });
    const response = await fetch(worker, { method: "POST", headers: { "content-type": "application/json", "x-sieve-worker": process.env.SIEVE_WORKER_SECRET ?? "" }, body: JSON.stringify({ job, submission }) });
    if (!response.ok) throw new Error(`worker returned ${response.status}`);
  } catch (error) {
    await store.set(`sieve:job:${job.id}`, { ...job, status: "failed", error: error instanceof Error ? error.message : "worker failed" }, { ex: RESULT_SECONDS });
  } finally {
    if (await store.get<string>("sieve:active") === job.id) await store.del("sieve:active");
  }
}

export async function readJob(request: Request, id: string): Promise<object> {
  const session = authenticated(request);
  if (!session) throw new Response("Unauthorized", { status: 401 });
  const job = await redis().get<LiveJob>(`sieve:job:${id}`);
  if (!job || job.owner !== session.id) throw new Response("Not found", { status: 404 });
  return job;
}
