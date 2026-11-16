import type { Piece, Settings, Volume } from "../api";

export type Config = {
  visible: number;
  hidden: number;
  connections: number;
  auto_continue: boolean;
  auto_finish: boolean;
  auto_restart_on_mistake: boolean;
};
export type Chunk = {
  start: number;
  end: number;
  section: number;
  label: string;
  focus: string;
};
export type Target = {
  id: string;
  kind: string;
  start: number;
  end: number;
  chunk: number;
  focus: string;
};
export type NoteError = {
  kind: string;
  id?: string;
  pitch: number;
  name: string;
  measure?: number;
  staff?: number;
};
export type Result = {
  passed: boolean;
  manual_accepted?: boolean;
  capture_ok?: boolean;
  notice: string;
  errors: NoteError[];
  error_count: number;
  errors_truncated?: boolean;
  assisted?: boolean;
  aborted?: boolean;
  restarted?: boolean;
  auto_restarted?: boolean;
};
export type Variant = {
  note_id: string;
  action: string;
  pitch: number;
  reason: string;
  measure: number;
  original_pitch: number;
  spelling?: { step: string; alter: number; octave: number } | null;
};
export type Snapshot = {
  lesson: {
    title: string;
    piece_id: string;
    source: { pdf_pages: [number, number] };
    plan_summary?: string;
    reference_status?: string;
    section_order?: number[];
    review_gaps?: string[];
    analysis_status: string;
    revision: string;
    scope: string;
    reviewer: string;
    corrections: unknown[];
    sections: { start: number; end: number; title: string }[];
  };
  ready: boolean;
  automatic_ready: boolean;
  source_notice: string;
  controller_error: string | null;
  target_page: number;
  profile: {
    previous_profile?: { revision: string };
    config: Config;
    hand?: "both" | "right" | "left";
    chunks: Chunk[];
    variants: Variant[];
    corrections?: Variant[];
    stage_index: number;
    generation: number;
    streak: number;
    completed: string[];
  };
  target: Target | null;
  learning_target: Target | null;
  review: {
    active: boolean;
    learned_start: number | null;
    current_start: number;
    learned_end: number | null;
    current_end: number | null;
  };
  active: {
    id: string;
    session_id: string;
    target: Target;
    assisted: boolean;
  } | null;
  pending_at: number | null;
  progress: { completed: number; total: number };
  history: {
    id: string;
    session_id: string | null;
    status: string;
    target: Target;
    result: Result | null;
  }[];
};
export type LearningProps = {
  pieces: Piece[];
  volumes: Volume[];
  settings: Settings;
  onError: (error: unknown) => void;
  onLibrary: () => void;
  onPieceChange: (pieceId: string) => void;
};
export type LessonChoice = { piece_id: string; title: string };
