export type BrowserJobStatus = "queued" | "running" | "complete" | "failed";

export interface BrowserJob {
  id: string;
  status: BrowserJobStatus;
  error?: string;
  report_path?: string;
}

export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));
}

export async function monitorLiveJob(
  id: string,
  onUpdate: (job: BrowserJob) => void,
  fetcher: FetchLike = window.fetch.bind(window),
  pollMs = 2_000,
): Promise<BrowserJob> {
  for (;;) {
    const response = await fetcher(`/api/jobs/${encodeURIComponent(id)}`, { credentials: "same-origin" });
    if (!response.ok) throw new Error("The live suite status could not be retrieved.");
    const job = await response.json() as BrowserJob;
    onUpdate(job);
    if (job.status === "complete" || job.status === "failed") return job;
    await delay(pollMs);
  }
}

export function privateReportUrl(id: string): string {
  return `/api/jobs/${encodeURIComponent(id)}/report`;
}
