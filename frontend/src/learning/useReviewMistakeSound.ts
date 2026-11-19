import { useEffect, useRef } from "react";
import type { Snapshot } from "./types";

/** Browser-local cue; never uses MIDI output, a microphone or a network. */
export function useReviewMistakeSound(data: Snapshot | null) {
  const context = useRef<AudioContext | null>(null);
  const heard = useRef(new Set<string>());
  const initialized = useRef(false);
  useEffect(() => {
    const unlock = () => {
      try {
        context.current ??= new AudioContext();
        void context.current.resume().catch(() => {});
      } catch {
        // Visual notification and capture remain available without audio.
      }
    };
    document.addEventListener("pointerdown", unlock);
    document.addEventListener("keydown", unlock);
    return () => {
      document.removeEventListener("pointerdown", unlock);
      document.removeEventListener("keydown", unlock);
      void context.current?.close().catch(() => {});
      context.current = null;
    };
  }, []);
  useEffect(() => {
    if (!data) return;
    const ids = data.history
      .filter(
        (take) => take.target.kind === "review" && take.result?.auto_restarted,
      )
      .map((take) => take.id);
    if (data.active?.mistake_detected) ids.push(data.active.id);
    // Existing history on opening Learning must not replay old alerts.
    const fresh =
      initialized.current && ids.some((id) => !heard.current.has(id));
    ids.forEach((id) => heard.current.add(id));
    initialized.current = true;
    const audio = context.current;
    if (!fresh || !audio || audio.state !== "running") return;
    try {
      const tone = audio.createOscillator();
      const volume = audio.createGain();
      tone.frequency.setValueAtTime(660, audio.currentTime);
      tone.frequency.setValueAtTime(440, audio.currentTime + 0.12);
      volume.gain.setValueAtTime(0, audio.currentTime);
      volume.gain.linearRampToValueAtTime(0.12, audio.currentTime + 0.01);
      volume.gain.linearRampToValueAtTime(0, audio.currentTime + 0.28);
      tone.connect(volume);
      volume.connect(audio.destination);
      tone.start();
      tone.stop(audio.currentTime + 0.3);
      tone.onended = () => {
        tone.disconnect();
        volume.disconnect();
      };
    } catch {
      // Audio output failures must never affect recording or retries.
    }
  }, [data]);
}
