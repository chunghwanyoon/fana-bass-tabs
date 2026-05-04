import { useEffect, useRef } from "react";
import {
  Formatter,
  Renderer,
  TabNote as VfTabNote,
  TabStave,
  Voice,
  VoiceMode,
} from "vexflow";
import type { Stave } from "vexflow";
import type { TabNote } from "../types";

const BEATS_PER_MEASURE = 4;
const LINE_HEIGHT = 140;

type TimedTab = TabNote & { beats: number; vexDur: string };

export function TabView({ tab, bpm }: { tab: TabNote[]; bpm: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.innerHTML = "";
    if (tab.length === 0) return;

    const beatsPerSecond = bpm / 60;
    const timed: TimedTab[] = tab.map((t) => {
      const beats = Math.max(t.duration * beatsPerSecond, 0.125);
      return { ...t, beats, vexDur: secondsToVexflow(beats) };
    });

    const measures = packMeasures(timed, BEATS_PER_MEASURE);
    const width = 900;
    const height = LINE_HEIGHT * measures.length + 20;

    const renderer = new Renderer(ref.current, Renderer.Backends.SVG);
    renderer.resize(width, height);
    const ctx = renderer.getContext();

    measures.forEach((line, idx) => {
      const y = 20 + idx * LINE_HEIGHT;
      const stave = new TabStave(10, y, width - 20);
      if (idx === 0) stave.addClef("tab");
      stave.setContext(ctx).draw();

      const vfNotes = line.map(
        (t) =>
          new VfTabNote({
            positions: [{ str: t.string, fret: t.fret }],
            duration: t.vexDur,
          })
      );

      const totalBeats = line.reduce((s, t) => s + t.beats, 0);
      const numBeats = Math.max(Math.round(totalBeats), 1);
      const voice = new Voice({ num_beats: numBeats, beat_value: 4 });
      voice.setMode(VoiceMode.SOFT);
      voice.addTickables(vfNotes);
      new Formatter().joinVoices([voice]).format([voice], width - 100);
      voice.draw(ctx, stave as unknown as Stave);
    });
  }, [tab, bpm]);

  return <div ref={ref} style={{ overflowX: "auto" }} />;
}

function packMeasures<T extends { beats: number }>(
  items: T[],
  beatsPerMeasure: number,
): T[][] {
  const out: T[][] = [];
  let cur: T[] = [];
  let cum = 0;
  for (const it of items) {
    if (cum > 0 && cum + it.beats > beatsPerMeasure + 0.001) {
      out.push(cur);
      cur = [];
      cum = 0;
    }
    cur.push(it);
    cum += it.beats;
  }
  if (cur.length) out.push(cur);
  return out;
}

const VEX_DURATIONS: { beats: number; dur: string }[] = [
  { beats: 4, dur: "w" },
  { beats: 3, dur: "hd" },
  { beats: 2, dur: "h" },
  { beats: 1.5, dur: "qd" },
  { beats: 1, dur: "q" },
  { beats: 0.75, dur: "8d" },
  { beats: 0.5, dur: "8" },
  { beats: 0.375, dur: "16d" },
  { beats: 0.25, dur: "16" },
  { beats: 0.125, dur: "32" },
];

function secondsToVexflow(beats: number): string {
  // 로그 거리 기준으로 가장 가까운 표준 음표 길이 선택 (2배/0.5배가 동등하게 멀어짐)
  let best = VEX_DURATIONS[0];
  let bestDist = Math.abs(Math.log(beats / best.beats));
  for (const c of VEX_DURATIONS) {
    const d = Math.abs(Math.log(beats / c.beats));
    if (d < bestDist) {
      best = c;
      bestDist = d;
    }
  }
  return best.dur;
}
