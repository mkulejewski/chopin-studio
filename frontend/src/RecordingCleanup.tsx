import { useEffect, useState } from "react";
import { api, json, clock, type Session } from "./api";
import { TouchButton as Button } from "./TouchButton";

export function DeleteConfirmation({
  title,
  description,
  busy,
  onCancel,
  onConfirm,
}: {
  title: string;
  description: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="modal-backdrop"
      onKeyDown={(e) => {
        if (e.key === "Escape" && !busy) onCancel();
      }}
    >
      <section
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
      >
        <h2>{title}</h2>
        <p>{description}</p>
        <p>
          This permanently removes the selected files from this app. It cannot
          be undone.
        </p>
        <div className="button-row">
          <Button
            autoFocus
            className="secondary"
            disabled={busy}
            onClick={onCancel}
          >
            Cancel
          </Button>
          <Button className="stop-button" disabled={busy} onClick={onConfirm}>
            {busy ? "Deleting…" : "Delete permanently"}
          </Button>
        </div>
      </section>
    </div>
  );
}

export function SessionDeleteButton({
  session,
  disabled = false,
  onDeleted,
  onError,
}: {
  session: Session;
  disabled?: boolean;
  onDeleted: () => void | Promise<void>;
  onError: (error: unknown) => void;
}) {
  const [confirm, setConfirm] = useState(false),
    [busy, setBusy] = useState(false);
  return (
    <>
      <Button
        className="secondary"
        disabled={
          disabled || busy || ["recording", "saving"].includes(session.status)
        }
        onClick={() => setConfirm(true)}
      >
        Delete session
      </Button>
      {confirm && (
        <DeleteConfirmation
          title="Delete this session?"
          busy={busy}
          description={`${session.name.replaceAll("_", " ")} · ${clock(session.duration)}. All MIDI, microphone audio, rendered audio, activities and reports belonging to this session will be removed.`}
          onCancel={() => setConfirm(false)}
          onConfirm={() => {
            void (async () => {
              setBusy(true);
              try {
                await api(
                  `/sessions/${session.id}`,
                  json("DELETE", { confirmation: "delete" }),
                );
                setConfirm(false);
                await onDeleted();
              } catch (e) {
                setConfirm(false);
                onError(e);
              } finally {
                setBusy(false);
              }
            })();
          }}
        />
      )}
    </>
  );
}

type Take = {
  id: string;
  session_id: string;
  title: string | null;
  piece_id: string | null;
  opus: string | null;
  start: number;
  end: number;
  started: string;
  revision: number;
  eligible: boolean;
  complete: boolean;
  choice: "auto" | "keep" | "remove";
  action: "keep" | "remove";
  reason: string;
  eligibility_reason: string;
  ranking_notice: string;
  pitch_score: number | null;
};
type Inventory = {
  takes: Take[];
  sessions: (Session & {
    bytes: number;
    audio_bytes: number;
    timeline_locked: boolean;
  })[];
  policy: string;
};

export function RecordingCleanup({
  onChanged,
  onOpen,
  onError,
}: {
  onChanged: () => void | Promise<void>;
  onOpen: (session: Session, segmentId: string) => void;
  onError: (e: unknown) => void;
}) {
  const [data, setData] = useState<Inventory | null>(null),
    [filter, setFilter] = useState("flagged"),
    [busy, setBusy] = useState(false),
    [confirm, setConfirm] = useState<Take | null>(null);
  const load = async () => setData(await api<Inventory>("/recordings"));
  useEffect(() => {
    void load().catch(onError);
    const timer = setInterval(() => {
      void load().catch(onError);
    }, 4000);
    return () => clearInterval(timer);
  }, []);
  const run = async (work: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await work();
      await load();
      await onChanged();
    } catch (e) {
      setConfirm(null);
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="chart-panel" aria-label="Audio cleanup">
      <h2>Audio cleanup</h2>
      <p>
        Default: keep audio for two complete or near-complete performances per
        piece. Other audio is flagged for removal. MIDI sessions are kept
        indefinitely. No files are deleted automatically.
      </p>
      <p>
        “Best” uses capture health, then a reliable verified-reference pitch
        score and clipping. Without a reliable score, the newest take wins ties.
        Listen before deleting audio; you can keep extra audio manually.
      </p>
      <label>
        Show audio recordings
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="flagged">Flagged audio</option>
          <option value="keep">Kept audio</option>
          <option value="all">All audio</option>
        </select>
      </label>
      {!data && <p>Loading audio recordings…</p>}
      {data && (
        <p>
          {data.takes.filter((t) => t.action === "keep").length} audio kept ·{" "}
          {data.takes.filter((t) => t.action === "remove").length} audio flagged
          ·{" "}
          {(data.sessions.reduce((n, s) => n + s.audio_bytes, 0) / 1e6).toFixed(
            1,
          )}{" "}
          MB of stored audio
        </p>
      )}
      {data?.takes
        .filter(
          (t) =>
            filter === "all" ||
            (filter === "flagged"
              ? t.action === "remove"
              : t.action === "keep"),
        )
        .map((t) => (
          <article
            className="chart-panel"
            key={t.id}
            data-audio-segment-id={t.id}
          >
            <h3>
              {t.title ? `${t.title} · ${t.opus}` : "Unidentified material"} ·{" "}
              {t.action === "keep" ? "Keep audio" : "Audio flagged for removal"}
            </h3>
            <p>
              {new Date(t.started).toLocaleString()} · {clock(t.start)}–
              {clock(t.end)}
              {t.pitch_score != null ? ` · pitch proxy ${t.pitch_score}%` : ""}
            </p>
            <p>
              {t.reason} {t.eligibility_reason} {t.ranking_notice}
            </p>
            <div className="button-row">
              <Button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  const session = data.sessions.find(
                    (s) => s.id === t.session_id,
                  );
                  if (session) onOpen(session, t.id);
                }}
              >
                Review take
              </Button>
              <Button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void run(() =>
                    api(
                      `/recordings/${t.id}`,
                      json("PUT", { choice: "auto", complete: !t.complete }),
                    ),
                  )
                }
              >
                {t.complete ? "Mark partial" : "Mark complete"}
              </Button>
              <Button
                className="secondary"
                disabled={busy || !t.eligible}
                onClick={() =>
                  void run(() =>
                    api(`/recordings/${t.id}`, json("PUT", { choice: "keep" })),
                  )
                }
              >
                Keep this audio
              </Button>
              <Button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void run(() =>
                    api(
                      `/recordings/${t.id}`,
                      json("PUT", { choice: "remove" }),
                    ),
                  )
                }
              >
                Flag audio for removal
              </Button>
              <Button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void run(() =>
                    api(`/recordings/${t.id}`, json("PUT", { choice: "auto" })),
                  )
                }
              >
                Use automatic choice
              </Button>
              <Button
                className="stop-button"
                disabled={busy}
                onClick={() => setConfirm(t)}
              >
                Delete audio
              </Button>
            </div>
          </article>
        ))}
      {data &&
        !data.takes.some(
          (t) =>
            filter === "all" ||
            (filter === "flagged"
              ? t.action === "remove"
              : t.action === "keep"),
        ) && (
          <p>
            No stored audio in this view. MIDI-only performances remain in
            session history.
          </p>
        )}
      {confirm && (
        <DeleteConfirmation
          title="Delete this audio?"
          busy={busy}
          description={`${confirm.title || "Unidentified material"} · ${clock(confirm.start)}–${clock(confirm.end)}. This removes microphone audio for this interval and generated audio for this take. MIDI files, MIDI exports, analyses and session history are retained. Other takes’ audio is preserved.`}
          onCancel={() => setConfirm(null)}
          onConfirm={() =>
            void run(async () => {
              await api(
                `/recordings/${confirm.id}/audio`,
                json("DELETE", {
                  confirmation: "delete",
                  revision: confirm.revision,
                }),
              );
              setConfirm(null);
            })
          }
        />
      )}
    </section>
  );
}
