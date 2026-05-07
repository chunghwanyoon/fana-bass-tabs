import { useRef, useState, type ChangeEvent } from "react";
import { API_BASE, enqueueFile, enqueueUrl, pollJob } from "./api";
import { ScoreView } from "./components/ScoreView";
import { TabView } from "./components/TabView";
import type { JobAccepted, TranscribeResult } from "./types";

const STAGES = [
  { id: "downloading", label: "오디오 다운로드", measurable: true },
  { id: "separating", label: "베이스 트랙 분리 (Demucs)", measurable: true },
  { id: "transcribing", label: "음 추출", measurable: false },
  { id: "scoring", label: "악보 생성", measurable: false },
] as const;

export function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const run = async (enqueue: () => Promise<JobAccepted>) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setStage("queued");
    setProgress(null);
    try {
      const { job_id } = await enqueue();
      const r = await pollJob(job_id, (s, p) => {
        setStage(s);
        setProgress(p);
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStage(null);
      setProgress(null);
    }
  };

  const handleUrl = () => url && run(() => enqueueUrl(url));
  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFileName(f.name);
      run(() => enqueueFile(f));
    }
  };

  return (
    <main>
      <header>
        <h1>
          <span className="logo">🎸</span> Fana Bass Tabs
        </h1>
        <p>YouTube/SoundCloud 링크 또는 음악 파일에서 베이스 악보와 타브를 자동 생성합니다.</p>
      </header>

      <section className="card input-card">
        <label className="field-label">YouTube · SoundCloud URL</label>
        <div className="row">
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
            onKeyDown={(e) => e.key === "Enter" && handleUrl()}
          />
          <button onClick={handleUrl} disabled={loading || !url}>
            {loading ? "처리 중" : "변환"}
          </button>
        </div>

        <div className="divider">또는</div>

        <input
          ref={fileRef}
          type="file"
          accept="audio/*"
          onChange={handleFile}
          disabled={loading}
          style={{ display: "none" }}
        />
        <button
          type="button"
          className="file-button"
          onClick={() => fileRef.current?.click()}
          disabled={loading}
        >
          📁 음악 파일 업로드
        </button>
        {fileName && <div className="file-name">{fileName}</div>}

        <div className="hint">
          짧은 곡 (30초 ~ 2분) 으로 시작하는 걸 추천합니다. 첫 변환은 모델 로드로 시간이 더 걸려요.
        </div>
      </section>

      {loading && <StepProgress current={stage} progress={progress} />}
      {error && <div className="error">⚠ {error}</div>}

      {result && (
        <>
          {result.title && <h2 className="result-title">{result.title}</h2>}
          <div className="card">
            <div className="meta">
              <span><strong>BPM</strong> {result.bpm.toFixed(1)}</span>
              <span><strong>튜닝</strong> {tuningLabel(result.tuning)}</span>
              <span><strong>트랜스크라이버</strong> {result.transcriber}</span>
              <span><strong>음 개수</strong> {result.notes.length}</span>
              <span className="job-id"><strong>job</strong> {result.job_id}</span>
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

      <VersionBadge />
    </main>
  );
}

function VersionBadge() {
  const builtAt = new Date(__APP_BUILT_AT__);
  const mm = String(builtAt.getMonth() + 1).padStart(2, "0");
  const dd = String(builtAt.getDate()).padStart(2, "0");
  const hh = String(builtAt.getHours()).padStart(2, "0");
  const min = String(builtAt.getMinutes()).padStart(2, "0");
  const shortDate = `${mm}/${dd} ${hh}:${min}`;
  const repoUrl = "https://github.com/chunghwanyoon/fana-bass-tabs";
  return (
    <a
      className="version-badge"
      href={`${repoUrl}/commit/${__APP_COMMIT__}`}
      target="_blank"
      rel="noopener noreferrer"
      title={`commit ${__APP_COMMIT__} · built ${__APP_BUILT_AT__}`}
    >
      <span>v {__APP_COMMIT__}</span>
      <span className="version-date">{shortDate}</span>
    </a>
  );
}

function StepProgress({
  current,
  progress,
}: {
  current: string | null;
  progress: number | null;
}) {
  if (current === null) return null;
  if (current === "queued") {
    return (
      <div className="steps">
        <div className="step active">
          <span className="dot" />
          <span className="step-label">큐에서 대기 중</span>
          <Bar progress={null} />
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
            <span className="step-label">{s.label}</span>
            <Bar progress={100} done />
          </div>
        ))}
      </div>
    );
  }
  const currentIdx = STAGES.findIndex((s) => s.id === current);
  return (
    <div className="steps">
      {STAGES.map((s, i) => {
        const isDone = i < currentIdx;
        const isActive = i === currentIdx;
        const cls = isDone ? "done" : isActive ? "active" : "";
        let barProgress: number | null = null;
        if (isDone) barProgress = 100;
        else if (isActive) {
          // 측정 가능한 단계는 실제 %, 아니면 indeterminate (null)
          barProgress = s.measurable ? (progress ?? 0) : null;
        } else barProgress = 0;
        return (
          <div key={s.id} className={`step ${cls}`}>
            <span className="dot" />
            <span className="step-label">{s.label}</span>
            <Bar
              progress={barProgress}
              done={isDone}
              indeterminate={isActive && !s.measurable}
            />
            {isActive && s.measurable && progress !== null && (
              <span className="step-pct">{progress}%</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Bar({
  progress,
  done = false,
  indeterminate = false,
}: {
  progress: number | null;
  done?: boolean;
  indeterminate?: boolean;
}) {
  if (indeterminate) {
    return (
      <div className="bar">
        <div className="bar-fill bar-indeterminate" />
      </div>
    );
  }
  const pct = progress === null ? 0 : Math.max(0, Math.min(100, progress));
  return (
    <div className="bar">
      <div
        className={`bar-fill${done ? " bar-done" : ""}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function tuningLabel(t: string): string {
  if (t === "5string") return "5현 (B-E-A-D-G)";
  if (t === "4string") return "4현 (E-A-D-G)";
  return t;
}
