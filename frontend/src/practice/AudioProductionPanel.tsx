import { useEffect, useState } from "react";
import { api, json, upload } from "../api";
import { TouchButton as Button } from "../TouchButton";
import type { Job, Segment } from "../types/practice";

type Props = {
  run: (fn: () => Promise<unknown>) => Promise<void>;
  dirty: boolean;
  busy: boolean;
  row: Segment;
  renderJobs: Job[];
  onError: (error: unknown) => void;
};

export function AudioProductionPanel({
  run,
  dirty,
  busy,
  row,
  renderJobs,
  onError,
}: Props) {
  const [ports, setPorts] = useState<string[]>([]);
  const [port, setPort] = useState("");
  const [captureDevice, setCaptureDevice] = useState("");
  const [fonts, setFonts] = useState<string[]>([]);
  const [font, setFont] = useState("");
  const [format, setFormat] = useState("wav");
  useEffect(() => {
    let live = true;
    void api<{ ports: string[] }>("/audio/hardware")
      .then((value) => {
        if (live) setPorts(value.ports);
      })
      .catch((error) => {
        if (live) onError(error);
      });
    void api<{ soundfonts: string[] }>("/audio/engines")
      .then((value) => {
        if (live) {
          setFonts(value.soundfonts);
          setFont(value.soundfonts[0] || "");
        }
      })
      .catch((error) => {
        if (live) onError(error);
      });
    return () => {
      live = false;
    };
  }, []);
  return (
    <details className="chart-panel optional-audio">
      <summary>Optional audio</summary>
      <p>
        Rendering starts only when requested. Original MIDI is retained.
        Page-control pedal messages are excluded from generated sound.
      </p>
      <h3>AP-470 built-in sound</h3>
      <p>
        Record WAV to a USB flash drive while playing, or replay this take
        through the physical piano. Computer USB carries MIDI. For computer
        audio capture, connect PHONES/OUTPUT to an audio interface and enter its
        ALSA input device. Leave input blank to use the piano's USB flash
        recorder during playback.
      </p>
      <label>
        MIDI output
        <select value={port} onChange={(e) => setPort(e.target.value)}>
          <option value="">Choose the AP-470 output</option>
          {ports.map((p) => (
            <option key={p}>{p}</option>
          ))}
        </select>
      </label>
      <Button
        className="secondary"
        onClick={() =>
          void run(async () => {
            const value = await api("/audio/hardware");
            setPorts(value.ports);
          })
        }
      >
        Refresh MIDI outputs
      </Button>
      <label>
        Audio interface ALSA input (optional)
        <input
          value={captureDevice}
          onChange={(e) => setCaptureDevice(e.target.value)}
          placeholder="plughw:CARD=YourInterface,DEV=0"
        />
      </label>
      <Button
        className="secondary"
        disabled={dirty || busy || !port}
        onClick={() =>
          void run(() =>
            api(
              `/segments/${row.id}/ap470`,
              json("POST", { port, capture_device: captureDevice }),
            ),
          )
        }
      >
        {captureDevice
          ? "Play through AP-470 and capture audio"
          : "Play through AP-470 (start piano audio recorder first)"}
      </Button>
      <label>
        Attach AP-470 WAV to this activity
        <input
          type="file"
          accept=".wav"
          disabled={dirty || busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void run(() => upload(`/segments/${row.id}/audio`, file));
            e.target.value = "";
          }}
        />
      </label>
      <h3>Software soundfont</h3>
      <div className="form-grid">
        <label>
          Soundfont
          <select value={font} onChange={(e) => setFont(e.target.value)}>
            <option value="">Choose a local soundfont</option>
            {fonts.map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
        </label>
        <label>
          Custom SF2 / SF3 path
          <input
            placeholder="/home/you/Piano.sf2"
            value={font}
            onChange={(e) => setFont(e.target.value)}
          />
        </label>
        <label>
          Audio format
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="wav">WAV</option>
            <option value="flac">FLAC</option>
          </select>
        </label>
      </div>
      <Button
        className="secondary"
        disabled={dirty || busy || !font}
        onClick={() =>
          void run(() =>
            api(
              `/segments/${row.id}/render`,
              json("POST", { soundfont: font, format }),
            ),
          )
        }
      >
        Render this activity with FluidSynth
      </Button>
      {renderJobs.map((j) => (
        <div className="audio-result" key={j.id}>
          <span>
            {JSON.parse(j.result!).engine} ·{" "}
            {JSON.parse(j.result!).format.toUpperCase()}
          </span>
          <audio controls preload="none" src={`/api/audio/${j.id}`} />
          <a className="button secondary" href={`/api/audio/${j.id}`} download>
            Download audio
          </a>
        </div>
      ))}
    </details>
  );
}
