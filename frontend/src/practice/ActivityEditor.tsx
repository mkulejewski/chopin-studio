import type React from "react";
import { activityTypes } from "../activityTypes";
import { api, type Piece } from "../api";
import { TouchButton as Button } from "../TouchButton";
import type { Segment } from "../types/practice";

type Props = {
  row: Segment;
  change: (id: string, update: Partial<Segment>) => void;
  pieces: Piece[];
  split: number;
  setSplit: React.Dispatch<React.SetStateAction<number>>;
  setSegments: React.Dispatch<React.SetStateAction<Segment[]>>;
  setDirty: React.Dispatch<React.SetStateAction<boolean>>;
  segments: Segment[];
  dirty: boolean;
  busy: boolean;
  run: (fn: () => Promise<unknown>) => Promise<void>;
};

export function ActivityEditor({
  row,
  change,
  pieces,
  split,
  setSplit,
  setSegments,
  setDirty,
  segments,
  dirty,
  busy,
  run,
}: Props) {
  return (
    <div className="chart-panel">
      <h3>Edit selected activity</h3>
      <div className="form-grid">
        <label>
          Start in original session (seconds)
          <input
            aria-label="Segment start seconds"
            type="number"
            min="0"
            step=".01"
            value={row.start}
            onChange={(e) => change(row.id, { start: Number(e.target.value) })}
          />
        </label>
        <label>
          End in original session (seconds)
          <input
            aria-label="Segment end seconds"
            type="number"
            min="0"
            step=".01"
            value={row.end}
            onChange={(e) => change(row.id, { end: Number(e.target.value) })}
          />
        </label>
        <label>
          Piece
          <select
            value={row.piece_id || ""}
            onChange={(e) =>
              change(row.id, {
                piece_id: e.target.value || null,
                label: e.target.value ? "Manually identified" : "Unknown piece",
                confidence: 0,
              })
            }
          >
            <option value="">Unknown / technical material</option>
            {pieces.map((p) => (
              <option value={p.id} key={p.id}>
                {p.catalogue_path}
              </option>
            ))}
          </select>
        </label>
        <label>
          Activity type
          <select
            value={row.kind}
            onChange={(e) =>
              change(row.id, {
                kind: e.target.value,
                complete: ["complete", "full_exercise"].includes(
                  e.target.value,
                ),
              })
            }
          >
            {Object.entries(activityTypes).map(([kind, label]) => (
              <option key={kind} value={kind}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <p className="muted">
          Partial exercise means practising a section. Full-piece exercise means
          a whole-piece run-through with mistakes or restarts. Complete
          performance is a whole take; its label does not certify musical
          quality.
        </p>
        <label>
          First measure
          <input
            type="number"
            min="0"
            value={row.first_measure ?? ""}
            onChange={(e) =>
              change(row.id, {
                first_measure: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Last measure
          <input
            type="number"
            min="0"
            value={row.last_measure ?? ""}
            onChange={(e) =>
              change(row.id, {
                last_measure: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Label
          <input
            value={row.label}
            onChange={(e) => change(row.id, { label: e.target.value })}
          />
        </label>
        <label>
          Split at original-session seconds
          <input
            aria-label="Split time seconds"
            type="number"
            min={row.start}
            max={row.end}
            step=".01"
            value={split}
            onChange={(e) => setSplit(Number(e.target.value))}
          />
        </label>
      </div>
      <label className="toggle-row">
        Mark disposable (original retained)
        <input
          type="checkbox"
          checked={!!row.discarded}
          onChange={(e) => change(row.id, { discarded: e.target.checked })}
        />
      </label>
      <div className="button-row">
        <Button
          className="secondary"
          disabled={split <= row.start || split >= row.end}
          onClick={() => {
            const id = crypto.randomUUID().replaceAll("-", "");
            setSegments((items) =>
              items.flatMap((s) =>
                s.id === row.id
                  ? [
                      { ...s, end: split },
                      { ...s, id, start: split, group_id: null },
                    ]
                  : [s],
              ),
            );
            setDirty(true);
          }}
        >
          Split activity
        </Button>
        <Button
          className="secondary"
          disabled={segments.indexOf(row) === segments.length - 1}
          onClick={() => {
            const i = segments.indexOf(row),
              next = segments[i + 1];
            setSegments((items) =>
              items
                .filter((s) => s.id !== next.id)
                .map((s) =>
                  s.id === row.id
                    ? {
                        ...s,
                        end: next.end,
                        complete: false,
                        kind: "partial",
                      }
                    : s,
                ),
            );
            setDirty(true);
          }}
        >
          Merge with next
        </Button>
        <Button
          className="secondary"
          disabled={segments.indexOf(row) === 0}
          onClick={() => {
            const previous = segments[segments.indexOf(row) - 1];
            const group =
              previous.group_id || crypto.randomUUID().replaceAll("-", "");
            change(previous.id, { group_id: group });
            change(row.id, { group_id: group });
          }}
        >
          Group with previous attempt
        </Button>
      </div>
      <p className="muted">
        Save edits before exporting, analysing or rendering. You can correct
        boundaries numerically without precision dragging.
      </p>
      <div className="button-row">
        <Button
          className="secondary"
          disabled={dirty || !row.piece_id || busy}
          onClick={() =>
            void run(() => api(`/segments/${row.id}/learn`, { method: "POST" }))
          }
        >
          Remember labelled MIDI reference
        </Button>
      </div>
    </div>
  );
}
