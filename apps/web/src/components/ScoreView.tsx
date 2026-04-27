import { useEffect, useRef } from "react";
import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";

export function ScoreView({ musicxmlUrl }: { musicxmlUrl: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const osmd = new OpenSheetMusicDisplay(ref.current, {
      autoResize: true,
      backend: "svg",
      drawTitle: false,
    });
    osmd
      .load(musicxmlUrl)
      .then(() => osmd.render())
      .catch((e) => {
        console.error("OSMD load failed", e);
      });
  }, [musicxmlUrl]);

  return <div ref={ref} />;
}
