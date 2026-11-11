import type { Session } from "./api";

export type LearningDay = {
  kind: "learning";
  key: string;
  started: string;
  day: string;
  pieceId: string;
  title: string;
  opus: string;
  takes: Session[];
  duration: number;
  events: number;
};
export type SessionEntry =
  | LearningDay
  | { kind: "session"; key: string; started: string; session: Session };

/** Local calendar dates, including DST and UTC-midnight crossings. */
export function sessionEntries(
  sessions: Session[],
  timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone,
): SessionEntry[] {
  const format = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const groups = new Map<string, LearningDay>();
  const entries: SessionEntry[] = [];
  for (const session of sessions) {
    const date = new Date(session.started);
    if (
      session.source !== "learning" ||
      !session.learning_piece_id ||
      !Number.isFinite(date.getTime())
    ) {
      entries.push({
        kind: "session",
        key: session.id,
        started: session.started,
        session,
      });
      continue;
    }
    const parts = Object.fromEntries(
      format.formatToParts(date).map((part) => [part.type, part.value]),
    );
    const day = `${parts.year}-${parts.month}-${parts.day}`;
    const key = `learning:${session.learning_piece_id}:${day}`;
    let group = groups.get(key);
    if (!group) {
      group = {
        kind: "learning",
        key,
        day,
        pieceId: session.learning_piece_id,
        title: `Learning ${session.learning_piece_title || session.learning_piece_id} Session`,
        opus: session.learning_piece_opus || "",
        started: session.started,
        takes: [],
        duration: 0,
        events: 0,
      };
      groups.set(key, group);
      entries.push(group);
    }
    group.takes.push(session);
    group.duration += Math.max(0, session.duration || 0);
    group.events += Math.max(0, session.events || 0);
    if (Date.parse(session.started) > Date.parse(group.started))
      group.started = session.started;
  }
  const newest = (a: { started: string }, b: { started: string }) =>
    (Date.parse(b.started) || 0) - (Date.parse(a.started) || 0);
  for (const group of groups.values()) group.takes.sort(newest);
  return entries.sort(newest);
}

export function sessionDayLabel(day: string) {
  // Format the already determined calendar day without shifting it again.
  return new Date(`${day}T12:00:00Z`).toLocaleDateString(undefined, {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
