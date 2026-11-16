import type { Piece } from "../api";
import type { Analysis } from "./analysis";

export type PracticeDay = {
  day: string;
  sessions: number;
  recorded_seconds: number;
};
type AssessmentItem = {
  analysis_id: string;
  segment_id: string;
  session_id: string;
  performed: string;
  notes: number;
  assessment: Analysis["result"]["assessment"] | null;
};
export type Objective = {
  id: string;
  piece_id: string;
  title: string;
  category: string;
  first_measure: number | null;
  last_measure: number | null;
  completed: boolean | number;
  revision: number;
  created: string;
  seconds: number;
  attributions: {
    id: string;
    session_id: string;
    start: number;
    end: number;
  }[];
};
export type PracticeHistory = {
  notice: string;
  measures: {
    reference_id: string;
    reference_revision?: string;
    measure: number;
    attempts: number;
    seconds: number;
    latest: { missing: number; extra: number };
    history: {
      date: string;
      missing: number;
      extra: number;
      trusted: boolean;
    }[];
  }[];
  recurring_mistakes: {
    measure: number;
    kind: string;
    pitch: number;
    attempts: number;
    history: { date: string; segment_id: string; trusted: boolean }[];
  }[];
  retention: {
    first_measure: number;
    last_measure: number;
    hand: string;
    passes: number;
    tests: number;
    days_since_test: number | null;
    last_passed: boolean;
    last_manual_accepted?: boolean;
    longest_successful_gap_days?: number;
    review_due: boolean;
    manual_recollections: number;
    note_rules: string;
    revision: string;
  }[];
  objectives: Objective[];
};
export type ProgressPiece = Pick<
  Piece,
  | "id"
  | "title"
  | "genre"
  | "opus"
  | "mastery"
  | "intent"
  | "liking"
  | "forgotten"
> & {
  attempts: number;
  seconds: number;
  complete: number | null;
  last_practised: string | null;
  machine: {
    latest_performance: AssessmentItem | null;
    automatic_level:
      | (AssessmentItem & {
          assessment: NonNullable<AssessmentItem["assessment"]>;
        })
      | null;
    revision_suggestion: string | null;
    personal_notes: string;
    personal_level: number | null;
  };
  practice: PracticeHistory;
};
