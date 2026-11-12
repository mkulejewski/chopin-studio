import { useEffect, useRef, useState } from "react";
import type { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import type { NoteGroup } from "./AnalysisEvidence";
import { api } from "./api";
import { buildComparisonMusicXml, type ScoreView } from "./comparisonScore";
import { TouchButton as Button } from "./TouchButton";

type Projection = {
  attempt_id: string;
  active: boolean;
  expected_visible: boolean;
  played_attacks: number;
  groups: NoteGroup[];
  first_measure: number | null;
  last_measure: number | null;
  range_start: number | null;
  range_end: number | null;
  notice: string;
  uncertain: boolean;
};
export function LearningStaves({
  attemptId,
  active,
  revealExpected,
}: {
  attemptId: string;
  active: boolean;
  revealExpected: boolean;
}) {
  const [projection, setProjection] = useState<Projection | null>(null);
  const [failure, setFailure] = useState("");
  const [view, setView] = useState<ScoreView>("overlay");
  const [first, setFirst] = useState<number | null>(null);
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
  const context = `${attemptId}:${active}:${revealExpected}`;
  const [renderedContext, setRenderedContext] = useState("");
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const params = new URLSearchParams({
          show_expected: String(revealExpected),
        });
        if (first !== null) params.set("first_measure", String(first));
        const value = await api<Projection>(
          `/learning/e25-1/attempts/${attemptId}/staves?${params}`,
          { signal: controller.signal },
        );
        if (live) {
          setProjection(value);
          setRenderedContext(context);
          setFailure("");
        }
      } catch (error) {
        if (live && !controller.signal.aborted)
          setFailure(error instanceof Error ? error.message : String(error));
      } finally {
        if (live && active) timer = setTimeout(poll, 450);
      }
    };
    void poll();
    return () => {
      live = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [attemptId, active, revealExpected, first]);
  useEffect(() => {
    if (!frame.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(1, Math.floor(entry.contentRect.width))),
    );
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);
  const current =
    renderedContext === context && projection?.attempt_id === attemptId
      ? projection
      : null;
  const expected = !!current?.expected_visible && revealExpected;
  const layout = expected ? view : "played";
  const signature = JSON.stringify(current?.groups || []);
  useEffect(() => {
    if (!current?.groups.length || !canvas.current) {
      canvas.current?.replaceChildren();
      return;
    }
    let cancelled = false;
    let display: OpenSheetMusicDisplay | undefined;
    const render = async () => {
      try {
        const groups: NoteGroup[] = JSON.parse(signature);
        const xml = buildComparisonMusicXml(groups, layout, "strict", -4);
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
  }, [signature, layout, width, expected, context]);
  return (
    <section className="learning-staves" aria-label="Learning staff comparison">
      <h3>
        {active ? "Live note comparison" : "Played versus expected notes"}
      </h3>
      <p>{failure || current?.notice || "Listening for MIDI notes…"}</p>
      {current && (
        <p role="status">
          {current.played_attacks} played attacks
          {expected
            ? ` · ${current.first_measure === 0 ? "pickup" : `measure ${current.first_measure}`}`
            : " · played notes only"}
        </p>
      )}
      {expected && (
        <div className="learning-staves-tools">
          <label>
            Staff layout
            <select
              value={view}
              onChange={(event) => setView(event.target.value as ScoreView)}
            >
              <option value="overlay">Overlay</option>
              <option value="stacked">Expected above played</option>
              <option value="played">Played only</option>
              <option value="reference">Expected only</option>
            </select>
          </label>
          <Button
            disabled={
              current?.range_start === null ||
              current?.first_measure === current?.range_start
            }
            onClick={() =>
              setFirst(
                Math.max(current!.range_start!, current!.first_measure! - 1),
              )
            }
          >
            Previous measure
          </Button>
          <Button
            disabled={
              current?.range_end === null ||
              current?.last_measure === current?.range_end
            }
            onClick={() =>
              setFirst(
                Math.min(current!.range_end!, current!.first_measure! + 1),
              )
            }
          >
            Next measure
          </Button>
          <Button
            className={first === null ? "selected" : ""}
            onClick={() => setFirst(null)}
          >
            Follow latest notes
          </Button>
        </div>
      )}
      {expected && (
        <p className="muted">
          Grey: expected/pending · dark: played · red: provisional pitch
          differences. Final evaluation decides the take. Four-flat key signature;
          expected notes retain the score spelling. Note lengths are schematic.
        </p>
      )}
      {current?.uncertain && (
        <p className="warning-text">
          Alignment is ambiguous. Treat these positions as provisional.
        </p>
      )}
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
      {current?.groups.length === 0 && <p>No notes played yet.</p>}
      <small>{status}</small>
    </section>
  );
}
