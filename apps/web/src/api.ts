import type { TranscribeResult } from "./types";

export async function transcribeUrl(url: string): Promise<TranscribeResult> {
  const res = await fetch("/api/transcribe/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url: url }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function transcribeFile(file: File): Promise<TranscribeResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/transcribe/file", { method: "POST", body: form });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}
