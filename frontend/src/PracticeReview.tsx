import { useEffect, useState } from "react";
import { activityLabel } from "./activityTypes";
import {
  AnalysisEvidence,
  latestActivityAnalysis,
  type Analysis,
} from "./AnalysisEvidence";
import { api, clock, type Piece, type Session } from "./api";
import { ActivityEditor } from "./practice/ActivityEditor";
import { AudioProductionPanel } from "./practice/AudioProductionPanel";
import { MicrophonePlayback } from "./practice/MicrophonePlayback";
import { PracticeReportsPanel } from "./practice/PracticeReportsPanel";
import { SessionTimeline } from "./practice/SessionTimeline";
import { TouchButton as Button } from "./TouchButton";

import type { Job, PracticeReport, Segment } from "./types/practice";
export function PracticeReview({
  session,
  pieces,
  onError,
  initialSegmentId,
  mode = "session",
  analysisPending = false,
  onOpenAnalysis,
  onSelectSegment,
}: {
  session: Session;
  pieces: Piece[];
  onError: (error: unknown) => void;
  initialSegmentId?: string | null;
  mode?: "session" | "analysis";
  analysisPending?: boolean;
  onOpenAnalysis?: (segmentId: string) => void;
  onSelectSegment?: (segmentId: string) => void;
}) {
  const [segments, setSegments] = useState<Segment[]>([]),
    [revision, setRevision] = useState(0),
    [dirty, setDirty] = useState(false),
    [selected, setSelected] = useState(""),
    [split, setSplit] = useState(0),
    [jobs, setJobs] = useState<Job[]>([]),
    [analyses, setAnalyses] = useState<Analysis[]>([]),
    [reports, setReports] = useState<PracticeReport[]>([]),
    [busy, setBusy] = useState(false);
  const [timelineLocked, setTimelineLocked] = useState(false);
  const [timelineZoom, setTimelineZoom] = useState(1);
  useEffect(() => {
    setSelected(initialSegmentId || "");
  }, [session.id, initialSegmentId]);
  const load = async () => {
    void api(`/sessions/${session.id}/recording`)
      .then((info) => setTimelineLocked(!!info.timeline_locked))
      .catch(() => {});
    const s = await api<Segment[]>(`/sessions/${session.id}/segments`);
    setSegments(s);
    setRevision(Math.max(0, ...s.map((s) => s.revision)));
    setDirty(false);
  };
  const results = async () => {
    const [j, a, r] = await Promise.all([
      api<Job[]>("/jobs"),
      api<Analysis[]>(`/sessions/${session.id}/analyses`),
      api<PracticeReport[]>(`/sessions/${session.id}/reports`),
    ]);
    setJobs(j);
    setAnalyses(a);
    setReports(r);
  };
  useEffect(() => {
    void load().catch(onError);
    void results().catch(onError);
  }, [session.id]);
  useEffect(() => {
    const timer = setInterval(() => {
      void results().catch(() => {});
      if (!dirty) void load().catch(() => {});
    }, 2000);
    return () => clearInterval(timer);
  }, [session.id, dirty]);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await results();
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  const change = (id: string, update: Partial<Segment>) => {
    setSegments((items) =>
      items.map((s) => (s.id === id ? { ...s, ...update } : s)),
    );
    setDirty(true);
  };
  const row = segments.find((s) => s.id === selected);
  useEffect(() => {
    if (!segments.length) return;
    if (!segments.some((s) => s.id === selected))
      setSelected(
        segments.find((s) => !s.discarded)?.id || segments[0]?.id || "",
      );
  }, [segments, selected]);
  useEffect(() => {
    if (selected) onSelectSegment?.(selected);
  }, [selected, onSelectSegment]);
  const candidate = row
    ? latestActivityAnalysis(analyses, session.id, row.id)
    : undefined;
  const analysis =
    candidate?.result.segment_snapshot &&
    candidate.result.segment_snapshot.piece_id !== row?.piece_id
      ? undefined
      : candidate;
  const snapshot = analysis?.result.segment_snapshot;
  const stale =
    !!row &&
    (!snapshot ||
      ["piece_id", "start", "end", "revision", "discarded", "complete"].some(
        (key) => snapshot[key] !== row[key as keyof Segment],
      ));
  useEffect(() => {
    if (row) setSplit(Math.round(((row.start + row.end) / 2) * 100) / 100);
  }, [row?.id]);
  const renderJobs = jobs.filter(
    (j) =>
      j.kind === "render" &&
      j.status === "done" &&
      j.result &&
      JSON.parse(j.result).filename &&
      JSON.parse(j.result).session_id === session.id,
  );
  return (
    <div className="practice-review">
      {mode === "session" && (
        <div className="button-row">
          <a
            className="button secondary"
            href={`/api/sessions/${session.id}/bundle`}
          >
            Export MIDI, audio & reports bundle
          </a>
          <a
            className="button secondary"
            href={`/api/sessions/${session.id}/preanalysis`}
          >
            Export structured LLM preanalysis (JSON)
          </a>
        </div>
      )}
      {mode === "session" && (
        <SessionTimeline
          segments={segments}
          timelineLocked={timelineLocked}
          busy={busy}
          dirty={dirty}
          run={run}
          session={session}
          load={load}
          revision={revision}
          setTimelineZoom={setTimelineZoom}
        />
      )}
      {mode === "analysis" && (
        <div className="section-heading">
          <h2>Choose an activity</h2>
          <label>
            Piece or passage
            <select
              aria-label="Select analysis activity"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              {!segments.length && (
                <option value="">No activities available</option>
              )}
              {segments.map((s) => (
                <option key={s.id} value={s.id}>
                  {pieces.find((p) => p.id === s.piece_id)?.catalogue_path ||
                    s.piece_id ||
                    "Unidentified material"}{" "}
                  · {clock(s.start)}–{clock(s.end)} · {activityLabel(s.kind)}
                </option>
              ))}
            </select>
          </label>
          <p>
            Select a piece or passage above. Correct piece labels and boundaries
            in Sessions before analysing.
          </p>
        </div>
      )}
      {mode === "session" && (
        <div className="timeline-touch" aria-label="Activity timeline">
          {segments.map((s) => (
            <Button
              key={s.id}
              style={{ minWidth: 240 * timelineZoom }}
              className={
                selected === s.id ? "timeline-item selected" : "timeline-item"
              }
              onClick={() => {
                setSelected(s.id);
                setSplit(Math.round(((s.start + s.end) / 2) * 100) / 100);
              }}
            >
              <strong>
                {s.piece_id
                  ? pieces.find((p) => p.id === s.piece_id)?.catalogue_path ||
                    s.piece_id
                  : "Unidentified material"}
              </strong>
              <span>
                {clock(s.start)}–{clock(s.end)} · {s.label} · similarity{" "}
                {s.confidence.toFixed(2)}
              </span>
              <small>
                {activityLabel(s.kind)} ·{" "}
                {s.first_measure != null
                  ? `Measures ${s.first_measure}–${s.last_measure}`
                  : "No reliable score measures"}
                {s.group_id ? " · Repeated-attempt group" : ""}
                {s.recording_deleted
                  ? " · Recording deleted"
                  : s.discarded
                    ? " · Disposable"
                    : ""}
              </small>
            </Button>
          ))}
        </div>
      )}
      {!segments.length && (
        <p className="muted">
          Waiting for candidate organisation. Silence-only recordings have no
          musical activities.
        </p>
      )}
      {mode === "session" &&
        row &&
        !row.recording_deleted &&
        !timelineLocked && (
          <ActivityEditor
            row={row}
            change={change}
            pieces={pieces}
            split={split}
            setSplit={setSplit}
            setSegments={setSegments}
            setDirty={setDirty}
            segments={segments}
            dirty={dirty}
            busy={busy}
            run={run}
          />
        )}
      {row && (
        <div
          className={
            mode === "analysis"
              ? "analysis-activity-actions button-row"
              : "analysis-activity-actions chart-panel"
          }
        >
          {mode === "session" && (
            <>
              <h3>
                {pieces.find((p) => p.id === row.piece_id)?.catalogue_path ||
                  row.piece_id ||
                  "Unidentified material"}
              </h3>
              <p>
                {clock(row.start)}–{clock(row.end)} · {activityLabel(row.kind)}
                {row.recording_deleted ? " · Audio removed; MIDI retained" : ""}
              </p>
            </>
          )}
          {session.source !== "learning" && (
            <Button
              className="primary"
              disabled={dirty || busy || analysisPending}
              onClick={() => {
                if (mode === "session") onOpenAnalysis?.(row.id);
                else
                  void run(() =>
                    api(`/segments/${row.id}/analyse`, { method: "POST" }),
                  );
              }}
            >
              {busy || analysisPending
                ? "Analysing activity…"
                : mode === "analysis" && analysis
                  ? "Reanalyse activity"
                  : "Analyse activity"}
            </Button>
          )}
          <a
            className={`button secondary ${dirty ? "disabled-link" : ""}`}
            aria-disabled={dirty}
            href={dirty ? undefined : `/api/segments/${row.id}/midi`}
          >
            Export activity MIDI
          </a>
          {mode === "session" && session.source !== "learning" && (
            <p className="muted">
              Opens this activity in Analysis. Save timeline edits first.
            </p>
          )}
        </div>
      )}
      {mode === "analysis" &&
        (row && analysis ? (
          <AnalysisEvidence
            key={analysis.id}
            analysis={analysis}
            musicalKey={pieces.find((p) => p.id === row.piece_id)?.musical_key}
            title={`${pieces.find((p) => p.id === row.piece_id)?.catalogue_path || row.piece_id || "Unidentified material"} · ${clock(row.start)}–${clock(row.end)}`}
            stale={stale}
          />
        ) : (
          <p className="info-box">
            {row
              ? "No saved analysis for this activity. Choose Analyse activity to generate one."
              : "Select an activity to review its analysis."}
          </p>
        ))}
      {row && !row.recording_deleted && (
        <MicrophonePlayback
          sessionId={session.id}
          segmentId={row.id}
          dirty={dirty}
          revision={`${row.start}:${row.end}`}
        />
      )}
      {mode === "session" && row && !row.recording_deleted && (
        <AudioProductionPanel
          onError={onError}
          run={run}
          dirty={dirty}
          busy={busy}
          row={row}
          renderJobs={renderJobs}
        />
      )}
      {mode === "analysis" && (
        <PracticeReportsPanel
          session={session}
          busy={busy}
          run={run}
          onError={onError}
          reports={reports}
        />
      )}
      <div className="jobs-list" aria-label="Background jobs">
        {jobs
          .filter((j) => ["queued", "running", "failed"].includes(j.status))
          .slice(0, 6)
          .map((j) => (
            <div className="job-row" key={j.id}>
              <span>
                {j.kind} · {j.status}
                {j.error ? " · " + j.error : ""}
              </span>
              {["queued", "running"].includes(j.status) && (
                <Button
                  className="secondary"
                  onClick={() =>
                    void run(() =>
                      api(`/jobs/${j.id}/cancel`, { method: "POST" }),
                    )
                  }
                >
                  Cancel job
                </Button>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}
