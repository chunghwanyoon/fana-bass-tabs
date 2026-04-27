import { useEffect, useRef } from "react";
import { Formatter, Renderer, Stave, TabNote as VfTabNote, TabStave, Voice } from "vexflow";
import type { TabNote } from "../types";

const NOTES_PER_LINE = 8;

export function TabView({ tab }: { tab: TabNote[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.innerHTML = "";
    if (tab.length === 0) return;

    const width = 900;
    const lines = chunk(tab, NOTES_PER_LINE);
    const height = 140 * lines.length + 20;

    const renderer = new Renderer(ref.current, Renderer.Backends.SVG);
    renderer.resize(width, height);
    const ctx = renderer.getContext();

    lines.forEach((line, idx) => {
      const y = 20 + idx * 140;
      const stave = new TabStave(10, y, width - 20);
      if (idx === 0) stave.addClef("tab");
      stave.setContext(ctx).draw();

      const vfNotes = line.map(
        (t) =>
          new VfTabNote({
            positions: [{ str: t.string, fret: t.fret }],
            duration: "q",
          })
      );

      const voice = new Voice({ num_beats: line.length, beat_value: 4 });
      voice.addTickables(vfNotes);
      new Formatter().joinVoices([voice]).format([voice], width - 100);
      voice.draw(ctx, stave as unknown as Stave);
    });
  }, [tab]);

  return <div ref={ref} style={{ overflowX: "auto" }} />;
}

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}
