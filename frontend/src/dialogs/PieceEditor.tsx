import { Check } from "lucide-react";
import React from "react";
import { TouchButton } from "../TouchButton";
import { api, json, type Piece, type Volume } from "../api";

type Props = {
  run: (action: () => Promise<unknown>) => Promise<void>;
  edit: Piece;
  refresh: () => Promise<void>;
  setModal: React.Dispatch<
    React.SetStateAction<"edit" | "settings" | "stop" | "shutdown" | null>
  >;
  setEdit: React.Dispatch<React.SetStateAction<Piece | null>>;
  volumes: Volume[];
  busy: boolean;
};

export function PieceEditor({
  run,
  edit,
  refresh,
  setModal,
  setEdit,
  volumes,
  busy,
}: Props) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void run(async () => {
          await api(`/pieces/${edit.id}`, json("PUT", edit));
          await refresh();
          setModal(null);
        });
      }}
    >
      <div className="form-grid">
        {(["title", "genre", "opus", "musical_key"] as const).map((key) => (
          <label key={key}>
            {
              {
                title: "Title",
                genre: "Genre",
                opus: "Opus and number",
                musical_key: "Key",
              }[key]
            }
            <input
              required={key === "title" || key === "genre"}
              value={edit[key]}
              onChange={(e) => setEdit({ ...edit, [key]: e.target.value })}
            />
          </label>
        ))}
        <label>
          PDF volume
          <select
            value={edit.volume_id}
            onChange={(e) =>
              setEdit({
                ...edit,
                volume_id: e.target.value,
                start_page: null,
                end_page: null,
              })
            }
          >
            {volumes.map((v) => (
              <option key={v.id} value={v.id}>
                {v.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Practice status
          <select
            value={edit.practice_status}
            onChange={(e) =>
              setEdit({
                ...edit,
                practice_status: e.target.value,
                intent: e.target.value,
              })
            }
          >
            {[
              "To explore",
              "Learning",
              "Maintaining",
              "Resting",
              "Review",
              "Next",
              "Planned",
              "Dream",
            ].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          First PDF page (1-based)
          <input
            type="number"
            min="1"
            value={edit.start_page || ""}
            onChange={(e) =>
              setEdit({
                ...edit,
                start_page: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Last PDF page (inclusive)
          <input
            type="number"
            min="1"
            value={edit.end_page || ""}
            onChange={(e) =>
              setEdit({
                ...edit,
                end_page: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Printed first page label
          <input
            value={edit.printed_page}
            onChange={(e) => setEdit({ ...edit, printed_page: e.target.value })}
          />
        </label>
      </div>
      <div className="form-grid">
        <label>
          Your learning level (1–3)
          <input
            type="number"
            min="1"
            max="3"
            step=".5"
            value={edit.mastery ?? ""}
            onChange={(e) =>
              setEdit({
                ...edit,
                mastery: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Special liking (0–3 pluses)
          <input
            type="number"
            min="0"
            max="3"
            value={edit.liking}
            onChange={(e) =>
              setEdit({ ...edit, liking: Number(e.target.value) })
            }
          />
        </label>
        <label>
          Repertoire intention
          <select
            value={edit.intent}
            onChange={(e) =>
              setEdit({
                ...edit,
                intent: e.target.value,
                practice_status: e.target.value,
              })
            }
          >
            {[
              "Learning",
              "Maintaining",
              "Review",
              "Next",
              "Planned",
              "Dream",
              "To explore",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Preferred edition
          <input
            value={edit.preferred_edition}
            onChange={(e) =>
              setEdit({
                ...edit,
                preferred_edition: e.target.value,
              })
            }
          />
        </label>
        <label className="toggle-row">
          Largely forgotten (X)
          <input
            type="checkbox"
            checked={!!edit.forgotten}
            onChange={(e) => setEdit({ ...edit, forgotten: e.target.checked })}
          />
        </label>
      </div>
      <label>
        Practice notes
        <textarea
          rows={3}
          value={edit.notes}
          onChange={(e) => setEdit({ ...edit, notes: e.target.value })}
        />
      </label>
      <p className="muted">
        PDF page numbers are counted from 1, including cover pages. Printed page
        labels are separate.
      </p>
      <TouchButton className="primary" disabled={busy}>
        <Check size={18} />
        Save piece
      </TouchButton>
    </form>
  );
}
