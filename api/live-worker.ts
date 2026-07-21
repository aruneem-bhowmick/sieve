import { Sandbox } from "@vercel/sandbox";
import { put } from "@vercel/blob";
import { Redis } from "@upstash/redis";

import { passwordAccepted } from "./_lib/session";
import { type SubmittedTask } from "./_lib/submission";

const TRUSTED_PACKAGE = JSON.stringify({ private: true, scripts: { test: "vitest run" } });

export default async function handler(request: Request): Promise<Response> {
  const workerSecret = process.env.SIEVE_WORKER_SECRET;
  if (request.method !== "POST" || !workerSecret || !passwordAccepted(request.headers.get("x-sieve-worker") ?? "", workerSecret)) return new Response("Unauthorized", { status: 401 });
  const body = await request.json() as { job: { id: string; owner: string; expiresAt: number }; submission: { tasks: SubmittedTask[] } };
  const snapshot = process.env.SIEVE_SANDBOX_SNAPSHOT_ID;
  const proxyUrl = process.env.SIEVE_TURN_PROXY_URL;
  if (!snapshot || !proxyUrl) return new Response("Live runner is not configured", { status: 503 });
  const store = Redis.fromEnv();
  const sandbox = await Sandbox.create({
    source: { type: "snapshot", snapshotId: snapshot }, timeout: 15 * 60 * 1000,
    env: { OPENAI_API_KEY: "sandbox-brokered" },
    networkPolicy: { allow: { "api.openai.com": [{ match: { path: { startsWith: "/v1/responses" }, method: ["POST"] }, forwardURL: proxyUrl }] } },
  });
  try {
    await Promise.all([
      store.set(`sieve:sandbox:${body.job.id}`, sandbox.name, { ex: 15 * 60 }),
      store.set(`sieve:sandbox-job:${sandbox.name}`, body.job.id, { ex: 15 * 60 }),
    ]);
    for (const task of body.submission.tasks) {
      for (const [path, content] of Object.entries(task.files)) await sandbox.fs.writeFile(`/vercel/sandbox/tasks/${task.task_id}/${path}`, content);
      await sandbox.fs.writeFile(`/vercel/sandbox/tasks/${task.task_id}/package.json`, TRUSTED_PACKAGE);
    }
    const run = await sandbox.runCommand("python", ["-m", "sieve", "run-suite", "--live", "--runs-dir", "/tmp/sieve-runs", "--report-path", "/tmp/report.html", "--model", "gpt-5.6-terra"]);
    const report = await sandbox.fs.readFile("/tmp/report.html", "utf8");
    if (run.exitCode !== 0) throw new Error((await run.stderr()).slice(-4000));
    await put(`sieve/${body.job.id}/report.html`, report, { access: "private", addRandomSuffix: false, contentType: "text/html" });
    await store.set(`sieve:job:${body.job.id}`, { ...body.job, status: "complete", report_path: `sieve/${body.job.id}/report.html` }, { ex: 24 * 60 * 60 });
    return Response.json({ status: "complete" });
  } catch (error) {
    await store.set(`sieve:job:${body.job.id}`, { ...body.job, status: "failed", error: error instanceof Error ? error.message : "sandbox failed" }, { ex: 24 * 60 * 60 });
    return new Response("Live suite failed", { status: 500 });
  } finally { await sandbox.stop(); }
}
