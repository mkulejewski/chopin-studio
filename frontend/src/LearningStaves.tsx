import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { ScoreView } from "./comparisonScore";
import { StaffNotation } from "./components/StaffNotation";
import { TouchButton as Button } from "./TouchButton";
import type { NoteGroup } from "./types/analysis";

type Projection = {
  follow_page?: number | null;
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
  key_fifths?: number;
};
export function LearningStaves({
  pieceId,
  attemptId,
  active,
  revealExpected,
  onFollowPage,
}: {
  pieceId: string;
  attemptId: string;
  active: boolean;
  revealExpected: boolean;
  onFollowPage?: (page: number | null) => void;
}) {
  const followCallback = useRef(onFollowPage);
  followCallback.current = onFollowPage;
  const [projection, setProjection] = useState<Projection | null>(null);
  const [failure, setFailure] = useState("");
  const [view, setView] = useState<ScoreView>("overlay");
  const [first, setFirst] = useState<number | null>(null);
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
          `/learning/${pieceId}/attempts/${attemptId}/staves?${params}`,
          { signal: controller.signal },
        );
        if (live) {
          followCallback.current?.(
            active && revealExpected && !value.uncertain
              ? (value.follow_page ?? null)
              : null,
          );
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
  }, [pieceId, attemptId, active, revealExpected, first]);
  const current =
    renderedContext === context && projection?.attempt_id === attemptId
      ? projection
      : null;
  const expected = !!current?.expected_visible && revealExpected;
  const layout = expected ? view : "played";
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
            Layout
            <select
              aria-label="Staff layout"
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
            aria-label="Previous measure"
            title="Previous measure"
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
            ‹ <span className="learning-wide-label">Previous</span>
          </Button>
          <Button
            aria-label="Next measure"
            title="Next measure"
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
            <span className="learning-wide-label">Next</span> ›
          </Button>
          <Button
            aria-label="Follow latest notes"
            title="Follow latest notes"
            className={first === null ? "selected" : ""}
            onClick={() => setFirst(null)}
          >
            Follow
          </Button>
        </div>
      )}
      {expected && (
        <details className="learning-notation-help">
          <summary>Notation key</summary>
          <p className="muted">
            Grey: expected/pending · dark: played · red: provisional pitch
            differences. Final evaluation decides the take. Four-flat key
            signature; expected notes retain the score spelling. Note lengths
            are schematic.
          </p>
        </details>
      )}
      {current?.uncertain && (
        <p className="warning-text">
          Alignment is ambiguous. Treat these positions as provisional.
        </p>
      )}
      <StaffNotation
        groups={current?.groups || []}
        context={context}
        layout={layout}
        expected={expected}
        fifths={current?.key_fifths ?? -4}
      />
      {current?.groups.length === 0 && <p>No notes played yet.</p>}
    </section>
  );
}
