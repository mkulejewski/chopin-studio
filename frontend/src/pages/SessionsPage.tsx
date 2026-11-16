import { ArrowLeft, ChevronRight, History, Upload } from "lucide-react";
import React from "react";
import { PracticeReview } from "../PracticeReview";
import { RecordingCleanup, SessionDeleteButton } from "../RecordingCleanup";
import { SessionsList } from "../SessionsList";
import { TouchButton } from "../TouchButton";
import { api, type Piece, type Session } from "../api";
import type { SessionSummary, Status } from "../appTypes";
import { SessionDetail } from "../components/AppPrimitives";

type Props = {
  midiImport: React.RefObject<HTMLInputElement | null>;
  setCleanupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  cleanupOpen: boolean;
  fail: (e: unknown) => void;
  refresh: () => Promise<void>;
  inspect: (
    s: Session,
    target?: string,
    segmentId?: string | null,
  ) => Promise<void>;
  selectedSession: Session | null;
  libraryView: "scores" | "recordings";
  setTab: (next: string) => void;
  libraryPiece: Piece | null;
  setSelectedSession: React.Dispatch<React.SetStateAction<Session | null>>;
  setSummary: React.Dispatch<React.SetStateAction<SessionSummary | null>>;
  sessionGroup: string | null;
  summary: SessionSummary | null;
  busy: boolean;
  status: Status | null;
  setReviewSegment: React.Dispatch<React.SetStateAction<string | null>>;
  setNotice: React.Dispatch<React.SetStateAction<string>>;
  pieces: Piece[];
  reviewSegment: string | null;
  run: (action: () => Promise<unknown>) => Promise<void>;
  sessions: Session[];
  setSessionGroup: React.Dispatch<React.SetStateAction<string | null>>;
};

export function SessionsPage({
  midiImport,
  setCleanupOpen,
  cleanupOpen,
  fail,
  refresh,
  inspect,
  selectedSession,
  libraryView,
  setTab,
  libraryPiece,
  setSelectedSession,
  setSummary,
  sessionGroup,
  summary,
  busy,
  status,
  setReviewSegment,
  setNotice,
  pieces,
  reviewSegment,
  run,
  sessions,
  setSessionGroup,
}: Props) {
  return (
    <section className="content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">EVERY HOUR COUNTS</span>
          <h1>Your practice sessions.</h1>
          <p>
            Keep your MIDI history, clean up audio, or delete accidental
            sessions. Learning takes are grouped by piece and local calendar
            day.
          </p>
        </div>
        <TouchButton
          className="secondary"
          onClick={() => midiImport.current?.click()}
        >
          <Upload size={19} />
          Import MIDI / CSV
        </TouchButton>
      </div>
      <div className="button-row">
        <TouchButton
          className="secondary"
          onClick={() => setCleanupOpen(!cleanupOpen)}
        >
          {cleanupOpen
            ? "Hide audio cleanup"
            : "Audio cleanup · kept & flagged recordings"}
        </TouchButton>
      </div>
      {cleanupOpen && (
        <RecordingCleanup
          onError={fail}
          onChanged={refresh}
          onOpen={(session, id) => {
            void inspect(session, "Sessions", id);
            setCleanupOpen(false);
          }}
        />
      )}
      {selectedSession ? (
        <>
          {libraryView === "recordings" && (
            <TouchButton
              className="text-button"
              onClick={() => setTab("Library")}
            >
              <ArrowLeft size={18} />
              Back to Recordings Library
            </TouchButton>
          )}
          {libraryPiece && (
            <TouchButton
              className="text-button"
              onClick={() => {
                setSelectedSession(null);
                setSummary(null);
                setTab("Library");
              }}
            >
              <ArrowLeft size={18} />
              Back to {libraryPiece.title} saved sessions
            </TouchButton>
          )}
          <TouchButton
            className="text-button"
            onClick={() => {
              setSelectedSession(null);
              setSummary(null);
            }}
          >
            <ArrowLeft size={18} />
            {sessionGroup && selectedSession.source === "learning"
              ? "Back to Learning Session"
              : "All sessions"}
          </TouchButton>
          <SessionDetail
            session={selectedSession}
            summary={summary}
            onDelete={
              <SessionDeleteButton
                session={selectedSession}
                onError={fail}
                disabled={busy || !!status?.active || !!status?.saving}
                onDeleted={async () => {
                  setSelectedSession(null);
                  setSummary(null);
                  setReviewSegment(null);
                  await refresh();
                  setNotice("Session deleted.");
                }}
              />
            }
            onAnalysis={() => setTab("Analysis")}
          />
          <PracticeReview
            key={selectedSession.id}
            session={selectedSession}
            pieces={pieces}
            onError={fail}
            initialSegmentId={reviewSegment}
            onSelectSegment={setReviewSegment}
            onOpenAnalysis={(segmentId) => {
              setReviewSegment(segmentId);
              setTab("Analysis");
              void run(() =>
                api(`/segments/${segmentId}/analyse`, { method: "POST" }),
              );
            }}
          />
        </>
      ) : sessions.length ? (
        <SessionsList
          sessions={sessions}
          disabled={busy || !!status?.active || !!status?.saving}
          initialGroup={sessionGroup}
          onOpen={(session, group) => {
            setSessionGroup(group);
            void inspect(session);
          }}
          onDeleted={refresh}
          onError={fail}
        />
      ) : (
        <div className="empty-panel">
          <History size={34} />
          <h2>Your first session starts at the piano.</h2>
          <p>
            Record freely or import a previous MIDI performance. No recording is
            created until you choose.
          </p>
          <TouchButton className="primary" onClick={() => setTab("Practice")}>
            Go to practice
            <ChevronRight size={18} />
          </TouchButton>
        </div>
      )}
    </section>
  );
}
