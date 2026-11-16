import { ChartNoAxesCombined } from "lucide-react";
import React from "react";
import { CompareTakes } from "../CompareTakes";
import { PracticeReview } from "../PracticeReview";
import { TouchButton } from "../TouchButton";
import { clock, type Piece, type Session } from "../api";
import { captureWarning } from "../captureWarning";

type Props = {
  fail: (e: unknown) => void;
  analysisSession: Session | null;
  sessions: Session[];
  inspect: (
    s: Session,
    target?: string,
    segmentId?: string | null,
  ) => Promise<void>;
  setSelectedSession: React.Dispatch<React.SetStateAction<Session | null>>;
  setReviewSegment: React.Dispatch<React.SetStateAction<string | null>>;
  practiceSessions: Session[];
  setCleanupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setTab: (next: string) => void;
  busy: boolean;
  pieces: Piece[];
  reviewSegment: string | null;
};

export function AnalysisPage({
  fail,
  analysisSession,
  sessions,
  inspect,
  setSelectedSession,
  setReviewSegment,
  practiceSessions,
  setCleanupOpen,
  setTab,
  busy,
  pieces,
  reviewSegment,
}: Props) {
  return (
    <section className="content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">LISTEN WITH CURIOSITY</span>
          <h1>A closer look at your playing.</h1>
          <p>
            Choose a Practice session or imported performance to review
            evidence, compare notes and generate a practice report.
          </p>
        </div>
      </div>
      <details className="chart-panel">
        <summary>Compare different takes of a piece</summary>
        <CompareTakes onError={fail} />
      </details>
      <label>
        Session
        <select
          aria-label="Select analysis session"
          value={analysisSession?.id || ""}
          onChange={(e) => {
            const s = sessions.find((s) => s.id === e.target.value);
            if (s) void inspect(s, "Analysis");
            else {
              setSelectedSession(null);
              setReviewSegment(null);
            }
          }}
        >
          <option value="">Choose a saved session</option>
          {practiceSessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name.replaceAll("_", " ")} ·{" "}
              {new Date(s.started).toLocaleString()} · {clock(s.duration)}
            </option>
          ))}
        </select>
      </label>
      {analysisSession ? (
        <>
          <div className="analysis-session-heading">
            <div>
              <h2>{analysisSession.name.replaceAll("_", " ")}</h2>
              <p>
                {new Date(analysisSession.started).toLocaleString()} ·{" "}
                {clock(analysisSession.duration)} · {analysisSession.status}
              </p>
            </div>
            <TouchButton
              className="secondary"
              onClick={() => {
                setCleanupOpen(false);
                setTab("Sessions");
              }}
            >
              Edit session timeline
            </TouchButton>
          </div>
          {captureWarning(analysisSession.error) && (
            <p className="info-box warning-text">
              {captureWarning(analysisSession.error)}
            </p>
          )}
          <PracticeReview
            key={`analysis-${analysisSession.id}`}
            mode="analysis"
            analysisPending={busy}
            session={analysisSession}
            pieces={pieces}
            onError={fail}
            initialSegmentId={reviewSegment}
            onSelectSegment={setReviewSegment}
          />
        </>
      ) : (
        <div className="empty-panel">
          <ChartNoAxesCombined size={36} />
          <h2>Start with a saved performance.</h2>
          <p>
            Choose a session above, or use Analyse activity in Sessions to open
            a specific piece or passage here.
          </p>
          <TouchButton className="secondary" onClick={() => setTab("Sessions")}>
            Browse sessions
          </TouchButton>
        </div>
      )}
    </section>
  );
}
