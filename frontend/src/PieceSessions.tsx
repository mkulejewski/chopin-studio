import { activityLabel } from "./activityTypes";
import { useEffect, useState } from "react";
import { api, clock, type Piece, type Session } from "./api";
import { TouchButton } from "./TouchButton";

type PieceSession = Session & {
  segments: {
    id: string;
    start: number;
    end: number;
    kind: string;
    audio_retention_action?: string | null;
  }[];
};

export function PieceSessions({
  piece,
  onOpen,
  onClose,
}: {
  piece: Piece;
  onOpen: (session: Session, segmentId: string) => void;
  onClose: () => void;
}) {
  const [sessions, setSessions] = useState<PieceSession[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setSessions(null);
    setError("");
    void api<PieceSession[]>(`/pieces/${piece.id}/sessions`)
      .then((rows) => {
        if (active) setSessions(rows);
      })
      .catch((e) => {
        if (active) setError(String(e));
      });
    return () => {
      active = false;
    };
  }, [piece.id]);
  return (
    <section aria-label="Saved sessions for this piece">
      <TouchButton className="text-button" onClick={onClose}>
        Back to library
      </TouchButton>
      <div className="section-heading">
        <h2>
          {piece.title} · {piece.opus} — Saved sessions
        </h2>
        <p>
          All MIDI performances, including partial attempts, are retained. Audio
          cleanup flags apply only to audio recordings.
        </p>
      </div>
      {error && <p role="alert">{error}</p>}
      {!error && sessions === null && <p>Loading saved sessions…</p>}
      {sessions?.length === 0 && (
        <p>No saved sessions linked to this piece yet.</p>
      )}
      <div className="session-list">
        {sessions?.map((s) => (
          <article key={s.id}>
            <h3>{s.name.replaceAll("_", " ")}</h3>
            <p>
              {new Date(s.started).toLocaleString()} · {clock(s.duration)}{" "}
              recording
            </p>
            <div className="button-row">
              {s.segments.map((segment) => (
                <TouchButton
                  key={segment.id}
                  className="secondary"
                  onClick={() => onOpen(s, segment.id)}
                >
                  Review {clock(segment.start)}–{clock(segment.end)} ·{" "}
                  {activityLabel(segment.kind)}
                  {segment.audio_retention_action === "remove"
                    ? " · audio flagged for removal"
                    : segment.audio_retention_action === "review"
                      ? " · audio needs review"
                      : ""}
                </TouchButton>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
