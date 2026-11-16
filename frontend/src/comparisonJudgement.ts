import type { NoteGroup, NoteJudgement } from "./types/analysis";
export type ComparisonMode = "strict" | "musical";
export function comparisonJudgement(
  group: NoteGroup,
  pitch: number,
  side: "expected" | "observed",
  mode: ComparisonMode,
): NoteJudgement {
  if (mode === "strict")
    return {
      severity: "error",
      reason: "strict_difference",
      explanation: "Exact pitch differs from the digital reference.",
    };
  return (
    group.musical_context?.[side]?.[String(pitch)] || {
      severity: "review",
      reason: "analysis_needed",
      explanation:
        "This saved analysis has no musical-context judgement. Analyse the activity again; uncertainty stays blue.",
    }
  );
}
