import { useState, type ChangeEvent } from "react";
import { enqueueFile, enqueueUrl, pollJob } from "./api";
import { ScoreView } from "./components/ScoreView";
import { TabView } from "./components/TabView";
import type { JobAccepted, TranscribeResult } from "./types";

export function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (enqueue: () => Promise<JobAccepted>) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setStage("queued");
    try {
      const { job_id } = await enqueue();
      const r = await pollJob(job_id, setStage);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStage(null);
    }
  };

  const handleUrl = () => url && run(() => enqueueUrl(url));
  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) run(() => enqueueFile(f));
  };

  return (
    <main style={{ maxWidth: 960, margin: "0 auto" }}>
      <h1>Fana Bass Tabs</h1>
      <p>YouTube/SoundCloud 링크를 입력하거나 음악 파일을 업로드하세요.</p>

      <section style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          type="url"
          placeholder="https://youtube.com/..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          style={{ flex: 1, padding: 8 }}
        />
        <button onClick={handleUrl} disabled={loading || !url}>
          {loading ? "처리 중..." : "변환"}
        </button>
      </section>

      <section style={{ marginBottom: 24 }}>
        <input type="file" accept="audio/*" onChange={handleFile} disabled={loading} />
      </section>

      {loading && (
        <div style={{ marginBottom: 16, opacity: 0.8 }}>
          처리 중{stage ? ` — ${stageLabel(stage)}` : "..."}
        </div>
      )}

      {error && (
        <div style={{ color: "crimson", marginBottom: 16 }}>오류: {error}</div>
      )}

      {result && (
        <>
          <div style={{ fontSize: 14, opacity: 0.7, marginBottom: 8 }}>
            튜닝: {result.tuning} · 트랜스크라이버: {result.transcriber} · BPM: {result.bpm.toFixed(1)} · job: {result.job_id}
          </div>
          <h2>스코어</h2>
          <ScoreView musicxmlUrl={`/api${result.musicxml_url}`} />
          <h2>베이스 타브</h2>
          <TabView tab={result.tab} bpm={result.bpm} />
        </>
      )}
    </main>
  );
}

function stageLabel(stage: string): string {
  switch (stage) {
    case "queued":
      return "대기 중";
    case "downloading":
      return "오디오 다운로드 중";
    case "separating":
      return "베이스 트랙 분리 중 (Demucs)";
    case "transcribing":
      return "음 추출 중";
    case "scoring":
      return "악보 생성 중";
    case "complete":
      return "완료";
    default:
      return stage;
  }
}
