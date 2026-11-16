import { captureWarning } from "../captureWarning";
import type { Analysis } from "../types/analysis";

type Props = { audio: NonNullable<Analysis["result"]["audio"]> };

export function AudioEvidence({ audio }: Props) {
  return (
    <details className="chart-panel" open>
      <summary>Microphone analysis & MIDI correlation</summary>
      <p>
        Recorded RMS {audio.rms_dbfs?.toFixed(1)} dBFS · peak{" "}
        {audio.peak_dbfs?.toFixed(1)} dBFS · clipping{" "}
        {((audio.clipped_sample_fraction || 0) * 100).toFixed(3)}% ·{" "}
        {audio.acoustic_attacks} detected attacks ·{" "}
        {audio.coverage_seconds?.toFixed(1)} s covered
      </p>
      {captureWarning(audio.capture_error) && (
        <p role="alert">{captureWarning(audio.capture_error)}</p>
      )}
      <p>{audio.notice}</p>
      {audio.piano_presence && <p>{audio.piano_presence.notice}</p>}
      <p>
        Alignment: {audio.correlation?.status}.
        {audio.correlation?.status === "estimated" && (
          <>
            {" "}
            Audio minus MIDI offset{" "}
            {((audio.correlation.audio_minus_midi_seconds || 0) * 1000).toFixed(
              0,
            )}{" "}
            ms; {audio.correlation.matched_groups}/
            {audio.correlation.midi_groups} attack groups matched; median
            residual {audio.correlation.median_absolute_residual_ms?.toFixed(1)}{" "}
            ms.
          </>
        )}{" "}
        {audio.correlation?.notice}
      </p>
      {!!audio.correlation?.events?.length && (
        <details>
          <summary>Correlated attacks (session timestamps)</summary>
          <table>
            <thead>
              <tr>
                <th>MIDI seconds</th>
                <th>Audio seconds</th>
                <th>Residual ms</th>
                <th>Attack dBFS</th>
                <th>MIDI velocity</th>
              </tr>
            </thead>
            <tbody>
              {audio.correlation.events.slice(0, 100).map((event, i) => (
                <tr key={i}>
                  <td>{event.midi_time.toFixed(3)}</td>
                  <td>{event.audio_time.toFixed(3)}</td>
                  <td>{event.residual_ms.toFixed(1)}</td>
                  <td>{event.attack_dbfs.toFixed(1)}</td>
                  <td>{event.midi_velocity.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            First 100 matched attacks; the JSON analysis contains up to 2,000.
          </p>
        </details>
      )}
    </details>
  );
}
