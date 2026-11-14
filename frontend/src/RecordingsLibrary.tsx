import { captureWarning } from "./captureWarning";
import { Headphones, Music2 } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { api, clock, type Piece, type Session } from "./api";
import { activityLabel } from "./activityTypes";
import { TouchButton as Button } from "./TouchButton";

type AudioSource = { label: string; url: string };
type AudioSession = Session & { audio_sources: AudioSource[] };
type Segment = {
  id: string;
  session_id: string;
  piece_id: string | null;
  start: number;
  end: number;
  kind: string;
  discarded: boolean;
  audio_sources: AudioSource[];
};
type Inventory = { sessions: AudioSession[]; segments: Segment[] };
type Recording = {
  session: AudioSession;
  segment?: Segment;
  pieceId: string | null;
};

export function RecordingsLibrary({
  pieces,
  onOpen,
  onAnalyse,
  initialPiece,
  onSelectPiece,
}: {
  pieces: Piece[];
  initialPiece: string | null;
  onSelectPiece: (pieceId: string | null) => void;
  onOpen: (session: Session, segmentId: string | null) => void;
  onAnalyse: (session: Session, segmentId: string | null) => void;
}) {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(initialPiece);
  const [playback, setPlayback] = useState<string | null>(null);
  useEffect(() => onSelectPiece(selected), [selected, onSelectPiece]);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    void api<Inventory>("/recordings/library", { signal: controller.signal })
      .then(setInventory)
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      });
    return () => controller.abort();
  }, [refresh]);
  const groups = new Map<string, Recording[]>();
  const bySession = new Map<string, Segment[]>();
  for (const segment of inventory?.segments || []) {
    if (!segment.audio_sources?.length) continue;
    const rows = bySession.get(segment.session_id) || [];
    rows.push(segment);
    bySession.set(segment.session_id, rows);
  }
  for (const session of inventory?.sessions || []) {
    const segments = bySession.get(session.id);
    const recordings: Recording[] = segments?.length
      ? segments.map((segment) => ({
          session,
          segment,
          pieceId: segment.piece_id || session.learning_piece_id || null,
        }))
      : session.audio_sources?.length
        ? [{ session, pieceId: session.learning_piece_id || null }]
        : [];
    for (const row of recordings) {
      const key = row.pieceId || "unidentified";
      const items = groups.get(key) || [];
      items.push(row);
      groups.set(key, items);
    }
  }
  const title = (id: string) =>
    pieces.find((p) => p.id === id)?.catalogue_path ||
    (id === "unidentified" ? "Unidentified recordings" : id);
  const visible = [...groups.entries()]
    .filter(([id]) =>
      title(id).toLocaleLowerCase().includes(search.toLocaleLowerCase()),
    )
    .sort(
      ([a], [b]) =>
        (pieces.find((p) => p.id === a)?.genre || "ZZZ").localeCompare(
          pieces.find((p) => p.id === b)?.genre || "ZZZ",
        ) || title(a).localeCompare(title(b)),
    );
  const rows = selected ? groups.get(selected) : null;
  const selectedPiece = pieces.find((p) => p.id === selected);
  return (
    <section className="recordings-library" aria-label="Recordings Library">
      <div className="section-heading">
        <h2>Saved recordings, by piece</h2>
        <p>
          Listen to retained microphone recordings and rendered MIDI audio.
          MIDI-only takes and recordings whose audio was removed remain in
          Sessions.
        </p>
      </div>
      <div className="button-row recordings-toolbar">
        <Button className="secondary" onClick={() => setRefresh((n) => n + 1)}>
          Refresh recordings
        </Button>
        {selected && (
          <Button
            className="secondary"
            onClick={() => {
              setSelected(null);
              setPlayback(null);
            }}
          >
            All recorded pieces
          </Button>
        )}
      </div>
      {error && <p role="alert">{error}</p>}
      {!inventory && !error && <p>Loading recordings…</p>}
      {inventory && !selected && (
        <>
          <label className="recordings-search">
            Find a recorded piece
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Title, opus or key…"
            />
          </label>
          <div className="piece-grid recording-piece-grid">
            {visible.map(([id, items], index) => {
              const piece = pieces.find((p) => p.id === id);
              const genre = piece?.genre || "Unidentified recordings";
              const previous =
                index > 0
                  ? pieces.find((p) => p.id === visible[index - 1][0])?.genre ||
                    "Unidentified recordings"
                  : null;
              const duration = items.reduce(
                (sum, r) =>
                  sum +
                  (r.segment
                    ? r.segment.end - r.segment.start
                    : r.session.duration),
                0,
              );
              const sources = items.flatMap(
                (r) => r.segment?.audio_sources || r.session.audio_sources,
              );
              return (
                <Fragment key={id}>
                  {genre !== previous && (
                    <h2 className="genre-heading">
                      {piece ? `Chopin / ${genre}` : genre}
                    </h2>
                  )}
                  <article
                    className="piece-card recording-piece-card"
                    data-piece-id={id}
                  >
                    <div className="card-top">
                      <span className="eyebrow">
                        {piece?.genre || "Unidentified"}
                      </span>
                      <Headphones size={20} />
                    </div>
                    <h2>{piece?.title || "Unidentified recordings"}</h2>
                    {piece?.musical_key && (
                      <p className="piece-key">{piece.musical_key}</p>
                    )}
                    <p>{title(id)}</p>
                    <p>
                      {items.length}{" "}
                      {items.length === 1 ? "recording" : "recordings"} ·{" "}
                      {clock(duration)} recorded
                    </p>
                    <p>
                      Latest{" "}
                      {new Date(items[0].session.started).toLocaleDateString()}
                    </p>
                    <div className="score-badges">
                      {sources.some(
                        (s) => s.label === "Recorded microphone",
                      ) && <span className="available">Microphone audio</span>}
                      {sources.some(
                        (s) => s.label === "Rendered MIDI audio",
                      ) && (
                        <span className="available">Rendered MIDI audio</span>
                      )}
                    </div>
                    <div className="card-buttons">
                      <Button
                        className="primary"
                        onClick={() => {
                          setSelected(id);
                          setPlayback(null);
                        }}
                      >
                        <Music2 size={18} />
                        Open recordings
                      </Button>
                    </div>
                  </article>
                </Fragment>
              );
            })}
          </div>
          {!visible.length && (
            <p>
              {groups.size
                ? "No recorded pieces match your search."
                : "No saved audio recordings yet. Record microphone audio in Practice, or render a saved MIDI activity in Sessions."}
            </p>
          )}
        </>
      )}
      {selected && (
        <>
          <div className="recordings-piece-heading">
            <span className="eyebrow">RECORDINGS FOR</span>
            <h2>{selectedPiece?.title || "Unidentified recordings"}</h2>
            {selectedPiece && (
              <p>
                {[
                  selectedPiece.opus && `Op. ${selectedPiece.opus}`,
                  selectedPiece.musical_key,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
            <p className="recordings-catalogue-path">
              {title(selected).replaceAll("/", " / ")}
            </p>
          </div>
          {!rows?.length && (
            <p>
              No audio recordings remain for this piece. Choose All recorded
              pieces to return.
            </p>
          )}
          <div className="session-list recording-detail-list">
            {rows?.map((r) => (
              <article
                className="recording-detail-card"
                key={r.segment?.id || r.session.id}
                data-recording-id={r.segment?.id || r.session.id}
              >
                <h3>{r.session.name.replaceAll("_", " ")}</h3>
                <p className="recording-metadata">
                  <span>{new Date(r.session.started).toLocaleString()}</span>{" "}
                  <span>
                    {r.session.source === "learning"
                      ? "Learning"
                      : "Practice / imported"}
                  </span>{" "}
                  <span className="recording-status">{r.session.status}</span>
                </p>
                <p className="recording-passage">
                  {r.segment
                    ? `${clock(r.segment.start)}–${clock(r.segment.end)} · ${activityLabel(r.segment.kind)}`
                    : clock(r.session.duration)}
                  {r.segment?.discarded
                    ? " · Flagged disposable; MIDI retained"
                    : ""}
                </p>
                {captureWarning(r.session.error) && (
                  <p className="warning-text recording-capture-warning">
                    {captureWarning(r.session.error)}
                  </p>
                )}
                <div className="button-row recording-actions">
                  <Button
                    className="secondary"
                    onClick={() => onOpen(r.session, r.segment?.id || null)}
                  >
                    Review recording
                  </Button>
                  {r.session.source !== "learning" && (
                    <Button
                      className="primary"
                      onClick={() =>
                        onAnalyse(r.session, r.segment?.id || null)
                      }
                    >
                      Open in Analysis
                    </Button>
                  )}
                  <a
                    className="button secondary"
                    download
                    href={
                      r.segment
                        ? `/api/segments/${r.segment.id}/midi`
                        : `/api/sessions/${r.session.id}/midi`
                    }
                  >
                    Download MIDI
                  </a>
                  <Button
                    className="secondary"
                    onClick={() => setPlayback(r.segment?.id || r.session.id)}
                  >
                    Listen to recording
                  </Button>
                </div>
                {playback === (r.segment?.id || r.session.id) && (
                  <RecordingPlayback
                    key={r.segment?.id || r.session.id}
                    recording={r}
                  />
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function RecordingPlayback({
  recording: { session, segment },
}: {
  recording: Recording;
}) {
  const sources = segment?.audio_sources || session.audio_sources;
  return (
    <div className="recording-playback">
      {sources.map((source) => (
        <div className="recording-audio-source" key={source.url}>
          <p>{source.label}</p>
          <div className="recording-audio-controls">
            <audio
              controls
              preload="none"
              src={source.url}
              aria-label={source.label}
            />
            <a className="button secondary" href={source.url} download>
              Download audio
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}
