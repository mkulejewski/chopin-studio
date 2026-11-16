import {
  BookOpen,
  GraduationCap,
  History,
  SlidersHorizontal,
  Star,
  Upload,
} from "lucide-react";
import React from "react";
import { PieceSessions } from "../PieceSessions";
import { RecordingsLibrary } from "../RecordingsLibrary";
import { References } from "../References";
import { TouchButton } from "../TouchButton";
import { api, json, type Piece, type Session, type Volume } from "../api";

type Props = {
  libraryView: "scores" | "recordings";
  setLibraryView: React.Dispatch<React.SetStateAction<"scores" | "recordings">>;
  pieces: Piece[];
  recordingPiece: string | null;
  setRecordingPiece: React.Dispatch<React.SetStateAction<string | null>>;
  setLibraryPiece: React.Dispatch<React.SetStateAction<Piece | null>>;
  setCleanupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  inspect: (
    s: Session,
    target?: string,
    segmentId?: string | null,
  ) => Promise<void>;
  libraryPiece: Piece | null;
  setReviewSegment: React.Dispatch<React.SetStateAction<string | null>>;
  search: string;
  setSearch: React.Dispatch<React.SetStateAction<string>>;
  filter: string;
  setFilter: React.Dispatch<React.SetStateAction<string>>;
  volumes: Volume[];
  run: (action: () => Promise<unknown>) => Promise<void>;
  refresh: () => Promise<void>;
  choose: (p: Piece) => void;
  openEdit: (p: Piece) => void;
  learningPieceIds: string[];
  busy: boolean;
  setLearningPieceId: React.Dispatch<React.SetStateAction<string>>;
  setTab: (next: string) => void;
  importVolume: React.RefObject<string>;
  pdfImport: React.RefObject<HTMLInputElement | null>;
  fail: (e: unknown) => void;
};

export function LibraryPage({
  libraryView,
  setLibraryView,
  pieces,
  recordingPiece,
  setRecordingPiece,
  setLibraryPiece,
  setCleanupOpen,
  inspect,
  libraryPiece,
  setReviewSegment,
  search,
  setSearch,
  filter,
  setFilter,
  volumes,
  run,
  refresh,
  choose,
  openEdit,
  learningPieceIds,
  busy,
  setLearningPieceId,
  setTab,
  importVolume,
  pdfImport,
  fail,
}: Props) {
  const filtered = pieces.filter(
    (p) =>
      (filter === "All pieces" ||
        p.genre === filter ||
        p.intent === filter ||
        (filter === "Favourites" && p.favourite) ||
        (filter === "Learning" && p.practice_status === "Learning")) &&
      `${p.title} ${p.opus} ${p.musical_key}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <section className="content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">A LIFETIME OF CHOPIN</span>
          <h1>
            {libraryView === "scores"
              ? "Your score library."
              : "Your recordings library."}
          </h1>
          <p>
            {libraryView === "scores"
              ? "Individual pieces. Familiar editions. All in one place."
              : "Saved performances and passages, organised by piece."}
          </p>
        </div>
        {libraryView === "scores" && (
          <TouchButton
            className="secondary"
            onClick={() =>
              document
                .getElementById("volume-imports")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            <Upload size={19} />
            Import a score
          </TouchButton>
        )}
      </div>
      <div
        className="button-row library-views"
        role="group"
        aria-label="Library views"
      >
        <TouchButton
          className={libraryView === "scores" ? "primary" : "secondary"}
          aria-pressed={libraryView === "scores"}
          onClick={() => setLibraryView("scores")}
        >
          Score Library
        </TouchButton>
        <TouchButton
          className={libraryView === "recordings" ? "primary" : "secondary"}
          aria-pressed={libraryView === "recordings"}
          onClick={() => setLibraryView("recordings")}
        >
          Recordings Library
        </TouchButton>
      </div>
      {libraryView === "recordings" ? (
        <RecordingsLibrary
          pieces={pieces}
          initialPiece={recordingPiece}
          onSelectPiece={setRecordingPiece}
          onOpen={(s, segmentId) => {
            setLibraryPiece(null);
            setCleanupOpen(false);
            void inspect(s, "Sessions", segmentId);
          }}
          onAnalyse={(s, segmentId) => {
            setLibraryPiece(null);
            void inspect(s, "Analysis", segmentId);
          }}
        />
      ) : libraryPiece ? (
        <PieceSessions
          key={libraryPiece.id}
          piece={libraryPiece}
          onClose={() => setLibraryPiece(null)}
          onOpen={(s, segmentId) => {
            void inspect(s);
            setReviewSegment(segmentId);
          }}
        />
      ) : (
        <>
          <div className="search-row">
            <input
              aria-label="Search pieces"
              placeholder="Search a title, opus or key…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              aria-label="Filter library"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              {[
                "All pieces",
                "Favourites",
                "Learning",
                "Nocturnes",
                "Études",
                "Preludes",
                "Waltzes",
                "Polonaises",
                "Mazurkas",
                "Impromptus",
                "Sonatas",
                "Ballades",
                "Review",
                "Next",
                "Planned",
                "Dream",
              ].map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </div>
          <div className="piece-grid">
            {filtered.map((p) => {
              const v = volumes.find((v) => v.id === p.volume_id);
              return (
                <React.Fragment key={p.id}>
                  {filtered.findIndex((x) => x.genre === p.genre) ===
                    filtered.indexOf(p) && (
                    <h2 className="genre-heading">Chopin / {p.genre}</h2>
                  )}
                  <article className="piece-card" data-piece-id={p.id}>
                    <div className="card-top">
                      <span className="eyebrow">{p.genre}</span>
                      <TouchButton
                        aria-label={`Favourite ${p.title} Op. ${p.opus}`}
                        className="icon-button"
                        onClick={() =>
                          void run(async () => {
                            await api(
                              `/pieces/${p.id}`,
                              json("PUT", {
                                ...p,
                                favourite: !p.favourite,
                              }),
                            );
                            await refresh();
                          })
                        }
                      >
                        <Star
                          size={20}
                          fill={p.favourite ? "#b39864" : "none"}
                        />
                      </TouchButton>
                    </div>
                    <h2>{p.title}</h2>
                    <p className="piece-key">{p.musical_key}</p>
                    <p>{p.catalogue_path}</p>
                    <p className="repertoire-state">
                      {p.intent}
                      {p.mastery != null
                        ? ` · your learning: ${p.mastery}/3`
                        : ""}
                      {p.liking ? ` · ${"+".repeat(p.liking)}` : ""}
                      {p.forgotten ? " · X — largely forgotten" : ""}
                    </p>
                    {p.notes && <p className="repertoire-note">{p.notes}</p>}
                    <div className="score-badges">
                      <span className={v?.filename ? "available" : ""}>
                        {v?.filename ? "PDF imported" : "PDF missing"}
                      </span>
                      <span className={p.reference_count ? "available" : ""}>
                        {p.reference_count
                          ? `${p.reference_count} symbolic reference${p.reference_count > 1 ? "s" : ""}`
                          : "No symbolic reference"}
                      </span>
                    </div>
                    <div className="card-buttons">
                      <TouchButton
                        className="primary"
                        onClick={() => choose(p)}
                      >
                        <BookOpen size={18} />
                        Open score
                      </TouchButton>
                      <TouchButton
                        className="icon-button"
                        aria-label={`Edit ${p.title} Op. ${p.opus}`}
                        onClick={() => openEdit(p)}
                      >
                        <SlidersHorizontal size={19} />
                      </TouchButton>
                      <TouchButton
                        className="secondary piece-sessions-button"
                        onClick={() => setLibraryPiece(p)}
                      >
                        <History size={18} />
                        Saved sessions
                      </TouchButton>
                      {learningPieceIds.includes(p.id) && (
                        <TouchButton
                          className="secondary piece-learning-button"
                          disabled={busy}
                          onClick={() =>
                            void run(async () => {
                              await api(
                                "/learning/selection",
                                json("POST", { piece_id: p.id }),
                              );
                              setLearningPieceId(p.id);
                              setTab("Learning");
                            })
                          }
                        >
                          <GraduationCap size={18} />
                          Open in Learning
                        </TouchButton>
                      )}
                    </div>
                  </article>
                </React.Fragment>
              );
            })}
          </div>
          {!filtered.length && (
            <p className="empty-message">No pieces match this filter.</p>
          )}
          <div className="section-heading" id="volume-imports">
            <h2>The Paderewski collection</h2>
            <p>
              Import a legally obtained PDF, then set each piece’s PDF page
              range. No scans are bundled.
            </p>
          </div>
          <div className="volume-list">
            {volumes.map((v) => (
              <div className="volume-row" key={v.id}>
                <div className="volume-icon">
                  <BookOpen />
                </div>
                <div>
                  <strong>{v.title}</strong>
                  <p>
                    {v.filename
                      ? `${v.pages} PDF pages · Stored locally`
                      : "Awaiting your PDF"}{" "}
                    ·{" "}
                    <a href={v.source} target="_blank" rel="noreferrer">
                      Source & attribution ↗
                    </a>
                  </p>
                </div>
                <TouchButton
                  className="secondary"
                  onClick={() => {
                    importVolume.current = v.id;
                    pdfImport.current?.click();
                  }}
                >
                  <Upload size={18} />
                  {v.filename ? "Replace PDF" : "Import PDF"}
                </TouchButton>
              </div>
            ))}
          </div>
          <References pieces={pieces} onError={fail} onChanged={refresh} />
        </>
      )}
    </section>
  );
}
