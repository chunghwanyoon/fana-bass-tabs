import type { JobAccepted, JobStatusResponse, TranscribeResult } from "./types";

// 개발 환경: VITE_API_BASE_URL 미설정 → "/api" 사용 (vite.config.ts 의 프록시가 :8000 으로 전달)
// 프로덕션 (Vercel): VITE_API_BASE_URL=https://<your-app>.fly.dev 등 절대 URL 주입
export const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function parseError(res: Response): Promise<string> {
  // FastAPI HTTPException 은 {"detail": "..."} 로 옴
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body);
  } catch {
    return await res.text();
  }
}

export async function enqueueUrl(
  url: string,
  timeSignature: string = "4/4",
): Promise<JobAccepted> {
  const res = await fetch(`${API_BASE}/transcribe/url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url: url, time_signature: timeSignature }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function enqueueFile(
  file: File,
  timeSignature: string = "4/4",
): Promise<JobAccepted> {
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams({ time_signature: timeSignature });
  const res = await fetch(`${API_BASE}/transcribe/file?${params}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getJob(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function pollJob(
  jobId: string,
  onUpdate: (stage: string | null, progress: number | null) => void,
  intervalMs = 1000,
): Promise<TranscribeResult> {
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const s = await getJob(jobId);
    onUpdate(s.stage, s.stage_progress);
    if (s.status === "complete" && s.result) return s.result;
    if (s.status === "failed") throw new Error(s.error || "Job failed");
    if (s.status === "not_found") throw new Error("Job not found");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
