export type Segment = {
  id: string;
  start: number;
  end: number;
  piece_id: string | null;
  label: string;
  confidence: number;
  first_measure: number | null;
  last_measure: number | null;
  kind: string;
  group_id: string | null;
  complete: boolean;
  discarded: boolean;
  revision: number;
  details: string;
  recording_deleted?: boolean;
};
export type Job = {
  id: string;
  kind: string;
  status: string;
  error: string | null;
  result: string | null;
};

export type PracticeReport = {
  id: string;
  session_id: string;
  created: string;
  provider: string;
  text: string;
};

export type PerformanceTake = Segment & {
  session_id: string;
  title: string | null;
  opus: string | null;
  started: string;
};
