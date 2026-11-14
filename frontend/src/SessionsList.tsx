import { captureWarning } from "./captureWarning";
import { useMemo, useState } from "react";
import { GraduationCap, ChevronRight, History } from "lucide-react";
import { clock, type Session } from "./api";
import { SessionDeleteButton } from "./RecordingCleanup";
import { sessionEntries, sessionDayLabel } from "./sessionGroups";
import { TouchButton as Button } from "./TouchButton";

export function SessionsList({
  sessions,
  disabled,
  onOpen,
  onDeleted,
  onError,
  initialGroup = null,
}: {
  sessions: Session[];
  disabled: boolean;
  onOpen: (session: Session, group: string | null) => void;
  onDeleted: () => void | Promise<void>;
  onError: (error: unknown) => void;
  initialGroup?: string | null;
}) {
  const entries = useMemo(() => sessionEntries(sessions), [sessions]);
  const [expanded, setExpanded] = useState<string | null>(initialGroup);
  const takeRow = (session: Session, group: string | null = null) => (
    <article key={session.id} data-session-id={session.id}>
      <Button className="session-row" onClick={() => onOpen(session, group)}>
        <div className="session-icon">
          <History size={22} />
        </div>
        <div>
          <h3>{session.name.replaceAll("_", " ")}</h3>
          <p>
            {new Date(session.started).toLocaleString()} ·{" "}
            {session.events.toLocaleString()} events · {session.status}
          </p>
          {captureWarning(session.error) && (
            <p className="warning-text">{captureWarning(session.error)}</p>
          )}
        </div>
        <span className="duration">{clock(session.duration)}</span>
        <ChevronRight size={20} />
      </Button>
      <SessionDeleteButton
        session={session}
        disabled={disabled}
        onDeleted={onDeleted}
        onError={onError}
      />
    </article>
  );
  return (
    <div className="session-list">
      {entries.map((entry) => {
        if (entry.kind === "session") return takeRow(entry.session);
        const open = expanded === entry.key;
        const region = `learning-day-${encodeURIComponent(entry.key)}`;
        const errors = entry.takes.filter((take) =>
          captureWarning(take.error),
        ).length;
        return (
          <article
            key={entry.key}
            className="learning-day-session"
            data-learning-group={entry.key}
          >
            <Button
              className="session-row learning-day-heading"
              aria-expanded={open}
              aria-controls={region}
              onClick={() => setExpanded(open ? null : entry.key)}
            >
              <div className="session-icon">
                <GraduationCap size={22} />
              </div>
              <div>
                <h3>{entry.title}</h3>
                <p>
                  {sessionDayLabel(entry.day)}
                  {entry.opus ? ` · Op. ${entry.opus}` : ""} ·{" "}
                  {entry.takes.length}{" "}
                  {entry.takes.length === 1 ? "take" : "takes"} ·{" "}
                  {entry.events.toLocaleString()} events
                </p>
                <p>
                  Learning and review takes ·{" "}
                  {open ? "Hide takes" : "Show takes"}
                </p>
                {errors > 0 && (
                  <p className="warning-text">
                    {errors} {errors === 1 ? "take has" : "takes have"}{" "}
                    recording issues
                  </p>
                )}
              </div>
              <span
                className="duration"
                title="Total recorded time, excluding breaks between takes"
              >
                {clock(entry.duration)}
              </span>
              <ChevronRight size={20} className={open ? "group-open" : ""} />
            </Button>
            {open && (
              <div
                id={region}
                className="learning-day-takes"
                role="region"
                aria-label={`${entry.title} · ${sessionDayLabel(entry.day)}`}
              >
                <p className="muted">
                  {entry.takes.length} individual takes. Open a take to review
                  or export it; Delete session below removes only that take.
                </p>
                {entry.takes.map((take) => takeRow(take, entry.key))}
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}
