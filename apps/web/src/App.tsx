import { useState, type ChangeEvent } from "react";
import { transcribeFile, transcribeUrl } from "./api";
import { ScoreView } from "./components/ScoreView";
import { TabView } from "./components/TabView";
import type { TranscribeResult } from "./types";

export function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<TranscribeResult>) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleUrl = () => url && run(() => transcribeUrl(url));
  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) run(() => transcribeFile(f));
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

      {error && (
        <div style={{ color: "crimson", marginBottom: 16 }}>오류: {error}</div>
      )}

      {result && (
        <>
          <div style={{ fontSize: 14, opacity: 0.7, marginBottom: 8 }}>
            튜닝: {result.tuning} · 트랜스크라이버: {result.transcriber} · job: {result.job_id}
          </div>
          <h2>스코어</h2>
          <ScoreView musicxmlUrl={`/api${result.musicxml_url}`} />
          <h2>베이스 타브</h2>
          <TabView tab={result.tab} />
        </>
      )}
    </main>
  );
}
