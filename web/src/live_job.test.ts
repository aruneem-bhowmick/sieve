import { describe, expect, it, vi } from "vitest";

import { monitorLiveJob, privateReportUrl } from "./live_job";

describe("live job monitoring", () => {
  it("reports queued progress then returns the completed job", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ id: "job-1", status: "queued" }))
      .mockResolvedValueOnce(Response.json({ id: "job-1", status: "complete", report_path: "sieve/job-1/report.html" }));
    const statuses: string[] = [];
    const monitored = monitorLiveJob("job-1", (job) => statuses.push(job.status), fetcher, 1);
    await vi.runAllTimersAsync();
    await expect(monitored).resolves.toMatchObject({ status: "complete" });
    expect(statuses).toEqual(["queued", "complete"]);
    expect(fetcher).toHaveBeenCalledWith("/api/jobs/job-1", { credentials: "same-origin" });
    vi.useRealTimers();
  });

  it("builds a same-origin, encoded private report route", () => {
    expect(privateReportUrl("job /1")).toBe("/api/jobs/job%20%2F1/report");
  });
});
