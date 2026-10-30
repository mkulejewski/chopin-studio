export async function api<T = any>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch("/api" + path, options);
  if (!response.ok) {
    let message = response.statusText;
    try {
      message = (await response.json()).detail || message;
    } catch {
      /* non-JSON error */
    }
    throw new Error(
      typeof message === "string" ? message : JSON.stringify(message),
    );
  }
  return response.json();
}
export const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export async function upload(path: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return api(path, { method: "POST", body: form });
}
export const clock = (seconds: number) => {
  const n = Math.floor(seconds);
  return `${Math.floor(n / 60)
    .toString()
    .padStart(2, "0")}:${(n % 60).toString().padStart(2, "0")}`;
};
export type Piece = {
  id: string;
  title: string;
  genre: string;
  opus: string;
  musical_key: string;
  volume_id: string;
  start_page: number | null;
  end_page: number | null;
  printed_page: string;
  favourite: number;
  practice_status: string;
  notes: string;
  view: string;
  composer: string;
  catalogue_path: string;
  mastery: number | null;
  liking: number;
  forgotten: boolean;
  intent: string;
  preferred_edition: string;
  reference_count: number;
};
export type Volume = {
  id: string;
  title: string;
  filename: string | null;
  pages: number | null;
  source: string;
  edition: string;
};
export type Session = {
  id: string;
  name: string;
  started: string;
  status: string;
  duration: number;
  events: number;
  source: string;
  error: string | null;
};
export type Settings = {
  preferred_device: string;
  pedal_enabled: boolean;
  pedal_controller?: number;
  separation_cooldown?: number;
  swipe: boolean;
  pinch: boolean;
  double_tap: boolean;
  tap_overlay: boolean;
  auto_hide: boolean;
  live_enabled?: boolean;
  live_auto_turn?: boolean;
  live_piece_id?: string | null;
  soundfont?: string;
};
