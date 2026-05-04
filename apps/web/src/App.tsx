import { useState, type ChangeEvent } from "react";
import { API_BASE, enqueueFile, enqueueUrl, pollJob } from "./api";
import { ScoreView } from "./components/ScoreView";
import { TabView } from "./components/TabView";
import type { JobAccepted, TranscribeResult } from "./types";

const STAGES = [
  { id: "downloading", label: "오디오 다운로드" },
  { id: "separating", label: "베이스 트랙 분리 (Demucs)" },
  { id: "transcribing", label: "음 추출" },
  { id: "scoring", label: "악보 생성" },
] as const;

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
    <main>
      <header>
        <h1>Fana Bass Tabs</h1>
        <p>YouTube/SoundCloud 링크 또는 음악 파일에서 베이스 악보와 타브를 자동 생성합니다.</p>
      </header>

      <section className="card">
        <div className="row">
          <input
            type="url"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
          <button onClick={handleUrl} disabled={loading || !url}>
            {loading ? "처리 중" : "변환"}
          </button>
        </div>

        <div className="divider">또는</div>

        <input type="file" accept="audio/*" onChange={handleFile} disabled={loading} />
      </section>

      {loading && <StepProgress current={stage} />}
      {error && <div className="error">⚠ {error}</div>}

      {result && (
        <>
          <h2>결과 정보</h2>
          <div className="card">
            <div className="meta">
              <span><strong>BPM</strong> {result.bpm.toFixed(1)}</span>
              <span><strong>튜닝</strong> {tuningLabel(result.tuning)}</span>
              <span><strong>트랜스크라이버</strong> {result.transcriber}</span>
              <span><strong>음 개수</strong> {result.notes.length}</span>
              <span><strong>job</strong> {result.job_id}</span>
            </div>
          </div>

          <h2>스코어 (베이스 클레프)</h2>
          <div className="score-wrap">
            <ScoreView musicxmlUrl={`${API_BASE}${result.musicxml_url}`} />
          </div>

          <h2>베이스 타브</h2>
          <div className="tab-wrap">
            <TabView tab={result.tab} bpm={result.bpm} />
          </div>
        </>
      )}
    </main>
  );
}

function StepProgress({ current }: { current: string | null }) {
  if (current === null) return null;
  if (current === "queued") {
    return (
      <div className="steps">
        <div className="step active">
          <span className="dot" />
          큐에서 대기 중
        </div>
      </div>
    );
  }
  if (current === "complete") {
    return (
      <div className="steps">
        {STAGES.map((s) => (
          <div key={s.id} className="step done">
            <span className="dot" />
            {s.label}
          </div>
        ))}
      </div>
    );
  }
  const currentIdx = STAGES.findIndex((s) => s.id === current);
  return (
    <div className="steps">
      {STAGES.map((s, i) => {
        const cls = i < currentIdx ? "done" : i === currentIdx ? "active" : "";
        return (
          <div key={s.id} className={`step ${cls}`}>
            <span className="dot" />
            {s.label}
          </div>
        );
      })}
    </div>
  );
}

function tuningLabel(t: string): string {
  if (t === "5string") return "5현 (B-E-A-D-G)";
  if (t === "4string") return "4현 (E-A-D-G)";
  return t;
}
