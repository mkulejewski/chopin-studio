import { useEffect, useState } from "react";
import { api } from "../api";

export function MicrophonePlayback({
  sessionId,
  segmentId,
  dirty,
  revision,
}: {
  sessionId: string;
  segmentId: string;
  dirty: boolean;
  revision: string;
}) {
  const [available, setAvailable] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setAvailable(false);
    const poll = async () => {
      try {
        const value = await api<{ microphone: boolean }>(
          `/segments/${segmentId}/audio-status`,
        );
        if (!cancelled) setAvailable(!!value.microphone);
      } catch {
        if (!cancelled) setAvailable(false);
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId, segmentId, revision]);
  if (!available) return null;
  return (
    <div className="chart-panel">
      <h3>Recorded microphone · selected activity</h3>
      <p>
        Uses the saved activity boundaries. Save timeline edits to update the
        audio cut. Only retained session audio is available after permanent
        deletions.
      </p>
      {!dirty && (
        <audio
          key={`${segmentId}:${revision}`}
          controls
          preload="none"
          src={`/api/segments/${segmentId}/microphone?bounds=${encodeURIComponent(revision)}`}
        />
      )}
      <div className="button-row">
        {!dirty && (
          <a
            className="button secondary"
            href={`/api/segments/${segmentId}/microphone`}
            download
          >
            Download activity FLAC
          </a>
        )}
        <a
          className="button secondary"
          href={`/api/sessions/${sessionId}/microphone`}
          download
        >
          Download retained session audio
        </a>
      </div>
    </div>
  );
}
