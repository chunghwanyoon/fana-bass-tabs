import type { JobAccepted, JobStatusResponse, TranscribeResult } from "./types";

export async function enqueueUrl(url: string): Promise<JobAccepted> {
  const res = await fetch("/api/transcribe/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url: url }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function enqueueFile(file: File): Promise<JobAccepted> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/transcribe/file", { method: "POST", body: form });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function pollJob(
  jobId: string,
  onStage: (stage: string | null) => void,
  intervalMs = 1500,
): Promise<TranscribeResult> {
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const s = await getJob(jobId);
    onStage(s.stage);
    if (s.status === "complete" && s.result) return s.result;
    if (s.status === "failed") throw new Error(s.error || "Job failed");
    if (s.status === "not_found") throw new Error("Job not found");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
