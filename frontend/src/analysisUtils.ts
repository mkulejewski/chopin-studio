import type { Analysis } from "./types/analysis";

export function latestActivityAnalysis(
  analyses: Analysis[],
  sessionId: string,
  segmentId: string,
) {
  return analyses
    .filter((a) => a.session_id === sessionId && a.segment_id === segmentId)
    .sort(
      (a, b) => b.created.localeCompare(a.created) || b.id.localeCompare(a.id),
    )[0];
}

export function midiNoteName(pitch: number) {
  return `${["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][pitch % 12]}${Math.floor(pitch / 12) - 1}`;
}
