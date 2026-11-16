import type React from "react";
import { api, json, type Session } from "../api";
import { TouchButton as Button } from "../TouchButton";
import type { Segment } from "../types/practice";

type Props = {
  segments: Segment[];
  timelineLocked: boolean;
  busy: boolean;
  dirty: boolean;
  run: (fn: () => Promise<unknown>) => Promise<void>;
  session: Session;
  load: () => Promise<void>;
  revision: number;
  setTimelineZoom: React.Dispatch<React.SetStateAction<number>>;
};

export function SessionTimeline({
  segments,
  timelineLocked,
  busy,
  dirty,
  run,
  session,
  load,
  revision,
  setTimelineZoom,
}: Props) {
  return (
    <>
      <div className="section-heading">
        <h2>Your activity timeline</h2>
        <p>
          Experimental candidate boundaries and piece matches. Check long
          expressive pauses and repeated sections. Original-session times stay
          exact.
        </p>
      </div>
      {timelineLocked && (
        <p className="info-box">
          Some recordings were permanently removed. Timeline boundaries and undo
          are locked so removed material cannot be restored. Change completeness
          and audio retention in Audio cleanup.
        </p>
      )}
      <div className="button-row">
        <Button
          className="secondary"
          disabled={busy || dirty || timelineLocked}
          onClick={() =>
            void run(async () => {
              await api(`/sessions/${session.id}/organise?force=true`, {
                method: "POST",
              });
            })
          }
        >
          Rebuild candidate timeline (undo available)
        </Button>
        <Button
          className="secondary"
          disabled={busy || timelineLocked}
          onClick={() =>
            void run(async () => {
              await api(`/sessions/${session.id}/segments/undo`, {
                method: "POST",
              });
              await load();
            })
          }
        >
          Undo last timeline edit
        </Button>
        {dirty && (
          <Button
            className="primary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await api(
                  `/sessions/${session.id}/segments`,
                  json("PUT", { segments, expected_revision: revision }),
                );
                await load();
              })
            }
          >
            Save timeline edits
          </Button>
        )}
      </div>
      <div className="button-row">
        <Button
          className="secondary"
          onClick={() => setTimelineZoom((z) => Math.max(0.75, z - 0.25))}
        >
          Zoom timeline out
        </Button>
        <Button
          className="secondary"
          onClick={() => setTimelineZoom((z) => Math.min(3, z + 0.25))}
        >
          Zoom timeline in
        </Button>
      </div>
    </>
  );
}
