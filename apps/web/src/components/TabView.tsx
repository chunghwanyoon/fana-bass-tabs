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

const LINE_HEIGHT = 130;
const STAVE_PADDING = 30;

type TimedTab = TabNote & { beats: number; vexDur: string };

export function TabView({
  tab,
  bpm,
  timeSignature = "4/4",
}: {
  tab: TabNote[];
  bpm: number;
  timeSignature?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.innerHTML = "";
    if (tab.length === 0) return;

    // 박자 분자/분모 → 한 마디 안에 들어가는 quarter-note 비트 수
    // 예) 6/8 → 6 * (4/8) = 3 quarter notes per measure
    const [num, denom] = parseTimeSig(timeSignature);
    const beatsPerMeasure = num * (4 / denom);

    const beatsPerSecond = bpm / 60;
    const timed: TimedTab[] = tab.map((t) => {
      const beats = Math.max(t.duration * beatsPerSecond, 0.125);
      return { ...t, beats, vexDur: secondsToVexflow(beats) };
    });

    const measures = packMeasures(timed, beatsPerMeasure);
    const width = 900;
    const height = LINE_HEIGHT * measures.length + STAVE_PADDING;

    const renderer = new Renderer(ref.current, Renderer.Backends.SVG);
    renderer.resize(width, height);
    const ctx = renderer.getContext();

    measures.forEach((line, idx) => {
      const y = STAVE_PADDING + idx * LINE_HEIGHT;
      const stave = new TabStave(10, y, width - 20);

      if (idx === 0) {
        stave.addClef("tab");
        stave.addTimeSignature(timeSignature);
      }
      stave.setMeasure(idx + 1);
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
  }, [tab, bpm, timeSignature]);

  return <div ref={ref} style={{ overflowX: "auto" }} />;
}

function parseTimeSig(ts: string): [number, number] {
  const [n, d] = ts.split("/").map(Number);
  if (!n || !d) return [4, 4];
  return [n, d];
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
