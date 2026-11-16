export type PassagePoint = {
  index: number;
  measure: number | null;
  beat: number;
  time: number | null;
  bpm: number | null;
  velocity: number | null;
  duration_ratio: number | null;
  pedal: number | null;
  release_velocity: number | null;
  missing: number[];
  extra: number[];
  dynamics: string[];
  melody_velocity?: number | null;
  bass_velocity?: number | null;
  inner_velocity?: number | null;
  pedal_changes?: { time: number; channel: number; value: number }[];
  voices: Record<string, number>;
  voicing: { against: string; melody_gap: number; status: string }[];
  notes: {
    pitch: number;
    velocity?: number;
    velocity_14?: number | null;
    release_velocity?: number | null;
    release_velocity_14?: number | null;
    duration: number;
    duration_beats?: number | null;
    duration_ratio?: number | null;
    voice_key?: string | null;
    role?: string | null;
    pedal?: number | null;
    dynamic?: string | null;
  }[];
};
export type PassageData = {
  reference_id: string;
  trusted: boolean;
  notice: string;
  measures?: {
    measure: number | null;
    voices: Record<string, number>;
    voicing: PassagePoint["voicing"];
  }[];
  points: PassagePoint[];
  voices: string[];
  release: {
    status: string;
    count: number;
    distinct_values: number;
    notice: string;
  };
  target: {
    roles?: Record<string, string>;
    melody_min_gap?: number | null;
    release_calibrated?: boolean;
  };
};
