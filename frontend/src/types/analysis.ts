import type { PassageData } from "./passages";

export type NoteJudgement = {
  severity: "error" | "review";
  reason: string;
  explanation: string;
};
export type NoteGroup = {
  key_fifths?: number | null;
  live_missing?: number[];
  live_neutral?: number[];
  measure: number | null;
  beat?: number;
  time: number | null;
  expected: number[];
  observed: number[];
  score_notes?: {
    pitch: number;
    key_fifths?: number | null;
    spelling?: { step: string; alter: number; octave: number } | null;
    correction?: {
      pitch: number;
      spelling?: { step: string; alter: number; octave: number } | null;
    };
    duration: number;
    staff?: number | null;
    display_staff?: number | null;
    staff_source?: string | null;
    clef_sign?: string | null;
    beam_group?: string | null;
    beaming_source?: string | null;
    beat_group_size?: number | null;
    measure_start?: number | null;
    voice?: string | null;
    part?: number | null;
    grace?: boolean | null;
  }[];
  played_notes?: { pitch: number; onset: number; duration: number }[];
  timing_review?: { ratio: number; explanation: string };
  musical_context?: {
    expected: Record<string, NoteJudgement>;
    observed: Record<string, NoteJudgement>;
  };
};
export type Observation = NoteGroup & {
  id: string;
  kind: string;
  pitch: number;
  uncertainty?: string;
  musical_judgement?: NoteJudgement;
};
export type Analysis = {
  id: string;
  session_id: string;
  segment_id: string;
  created: string;
  result: {
    key_fifths?: number | null;
    audio?: {
      available: boolean;
      notice: string;
      piano_presence?: {
        status: string;
        notice: string;
        auto_discard: boolean;
      } | null;
      discarded_for_headphone_play?: boolean;
      rms_dbfs?: number;
      peak_dbfs?: number;
      clipped_sample_fraction?: number;
      quiet_fraction?: number;
      capture_error?: string;
      acoustic_attacks?: number;
      coverage_seconds?: number;
      correlation?: {
        status: string;
        audio_minus_midi_seconds?: number;
        matched_groups?: number;
        midi_groups?: number;
        median_absolute_residual_ms?: number;
        notice: string;
        events?: {
          midi_time: number;
          audio_time: number;
          residual_ms: number;
          attack_dbfs: number;
          midi_velocity: number;
        }[];
      };
    };
    passages?: PassageData;
    midi_resolution?: Record<string, number>;
    notes: number;
    notice?: string;
    velocity_mean?: number;
    observations?: Observation[];
    observations_truncated?: boolean;
    note_comparison?: NoteGroup[];
    unaligned_played_groups?: number;
    reference_quality?: string;
    musical_review?: {
      version: string;
      red_pitch_differences: number;
      blue_pitch_differences: number;
      notice: string;
      timing_flags: {
        measure: number | null;
        time: number;
        ratio: number;
        explanation: string;
        severity: string;
      }[];
    };
    segment_snapshot?: Record<string, unknown>;
    assessment?: {
      piece_level?: string | null;
      capture_ok?: boolean;
      precision_score: number;
      level?: string | null;
      audio_candidate?: boolean;
      coverage: number;
      pitch_precision: number;
      pitch_recall: number;
      notice: string;
    };
    tempo?: { bpm: number | null; notice?: string };
  };
};
