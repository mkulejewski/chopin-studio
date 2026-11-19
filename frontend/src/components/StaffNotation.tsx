import type { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { useEffect, useRef, useState } from "react";
import { buildComparisonMusicXml, type ScoreView } from "../comparisonScore";
import type { NoteGroup } from "../types/analysis";

export function StaffNotation({
  groups,
  context,
  layout,
  expected,
  fifths,
}: {
  groups: NoteGroup[];
  context: string;
  layout: ScoreView;
  expected: boolean;
  fifths: number;
}) {
  const [width, setWidth] = useState(320);
  const [status, setStatus] = useState("");
  const frame = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const committedDisplay = useRef<OpenSheetMusicDisplay | null>(null);
  useEffect(
    () => () => {
      committedDisplay.current?.clear();
      committedDisplay.current = null;
    },
    [],
  );
  useEffect(() => {
    if (!frame.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(1, Math.floor(entry.contentRect.width))),
    );
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);
  const signature = JSON.stringify(groups);
  useEffect(() => {
    if (signature === "[]" || !canvas.current) {
      canvas.current?.replaceChildren();
      return;
    }
    let cancelled = false;
    let display: OpenSheetMusicDisplay | undefined;
    const render = async () => {
      try {
        const notes: NoteGroup[] = JSON.parse(signature);
        const xml = buildComparisonMusicXml(notes, layout, "strict", fifths);
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        if (cancelled || !canvas.current) return;
        const target = document.createElement("div");
        target.style.width = `${Math.max(760, width)}px`;
        display = new OpenSheetMusicDisplay(target, {
          backend: "svg",
          autoResize: false,
          drawingParameters: "compacttight",
          drawTitle: false,
          drawComposer: false,
          drawPartNames: layout === "stacked",
          coloringEnabled: true,
          colorStemsLikeNoteheads: true,
          autoBeam: false,
          drawMeasureNumbers: expected,
          drawMeasureNumbersOnlyAtSystemStart: false,
          useXMLMeasureNumbers: true,
          drawTimeSignatures: false,
        });
        display.EngravingRules.SetWantedStemDirectionByXml = true;
        display.EngravingRules.RenderKeySignatures = true;
        display.Zoom = 0.85;
        await display.load(xml);
        if (cancelled || !canvas.current) return;
        // OSMD measures its attached container during render. Keep the old
        // engraving visible while this staging surface is being prepared.
        target.style.position = "absolute";
        target.style.visibility = "hidden";
        canvas.current.append(target);
        display.render();
        // Dense piano measures can exceed OSMD's container width. Scale the
        // complete engraving into the panel rather than cropping or scrolling.
        for (const svg of target.querySelectorAll("svg")) {
          const w = svg.width.baseVal.value;
          const h = svg.height.baseVal.value;
          if (w > 0 && h > 0) {
            svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
            svg.setAttribute("width", "100%");
            svg.removeAttribute("height");
            svg.style.height = "auto";
            svg.style.display = "block";
          }
        }
        target.style.width = "100%";
        target.style.position = "";
        target.style.visibility = "";
        const previous = committedDisplay.current;
        canvas.current.replaceChildren(target);
        committedDisplay.current = display;
        previous?.clear();
        setStatus("Live staves ready.");
      } catch (error) {
        if (!cancelled)
          setStatus(
            `Staff rendering unavailable: ${error instanceof Error ? error.message : String(error)}`,
          );
      }
    };
    void render();
    return () => {
      cancelled = true;
      if (display && committedDisplay.current !== display) display.clear();
    };
  }, [signature, fifths, layout, width, expected, context]);
  return (
    <>
      <div ref={frame} className="learning-staves-scroll">
        <div
          ref={canvas}
          key={context}
          role="img"
          aria-label={
            expected
              ? "Expected and played notes on staves"
              : "Played notes on staves"
          }
        />
      </div>
      <small>{status}</small>
    </>
  );
}
