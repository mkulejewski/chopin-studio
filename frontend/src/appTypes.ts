export type Status = {
  active: string | null;
  duration: number;
  events: number;
  error: string | null;
  devices: string[];
  connected: string | null;
  device_error: string | null;
  notes: Record<string, number>;
  pedals: Record<string, number>;
  recent: { at: number; message: string }[];
  queue_depth: number;
  last_event_age: number | null;
  simulation: boolean;
  event_rate: number;
  saving: boolean;
  shutting_down: boolean;
  midi_enabled?: boolean;
  microphone_enabled?: boolean;
};

export type PageCommand = {
  id: number;
  action: string;
  page?: number;
  piece_id?: string;
  actions?: { action: string }[];
};

export type SessionSummary = {
  notes: number;
  markers: { t: number; kind: string }[];
};
