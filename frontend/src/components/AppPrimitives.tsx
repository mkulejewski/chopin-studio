import { ChartNoAxesCombined, Download } from "lucide-react";
import React from "react";
import { createPortal } from "react-dom";
import { TouchButton } from "../TouchButton";
import { clock, type Session } from "../api";
import type { SessionSummary } from "../appTypes";
import { captureWarning } from "../captureWarning";

export function ModalBackdrop({
  host,
  children,
}: {
  host: HTMLElement | null;
  children: React.ReactNode;
}) {
  return createPortal(
    <div className="modal-backdrop">{children}</div>,
    host || document.body,
  );
}
export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
export function SessionDetail({
  session,
  summary,
  onAnalysis,
  onDelete,
}: {
  session: Session;
  summary: SessionSummary | null;
  onAnalysis: () => void;
  onDelete: React.ReactNode;
}) {
  return (
    <>
      <div className="detail-heading">
        <h2>{session.name.replaceAll("_", " ")}</h2>
        <p>
          {new Date(session.started).toLocaleString()} · {session.status}
        </p>
      </div>
      {captureWarning(session.error) && (
        <div className="info-box warning-text">
          {captureWarning(session.error)}
        </div>
      )}
      <div className="metric-grid">
        <Metric label="Recording length" value={clock(session.duration)} />
        <Metric label="MIDI events" value={session.events.toLocaleString()} />
        <Metric
          label="Note onsets"
          value={summary ? summary.notes.toLocaleString() : "…"}
        />
      </div>
      <div className="button-row">
        <a
          className="button primary"
          href={`/api/sessions/${session.id}/midi`}
          download
        >
          <Download size={19} />
          Export original MIDI
        </a>
        {session.source !== "learning" && (
          <TouchButton className="secondary" onClick={onAnalysis}>
            <ChartNoAxesCombined size={19} />
            Open session analysis
          </TouchButton>
        )}
        {onDelete}
      </div>
      {!!summary?.markers.length && (
        <div className="chart-panel">
          <h3>Connection & session markers</h3>
          {summary.markers.map((m, i) => (
            <p key={i}>
              {clock(m.t)} · {m.kind.replaceAll("_", " ")}
            </p>
          ))}
        </div>
      )}
    </>
  );
}
