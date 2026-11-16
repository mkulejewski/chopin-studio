import {
  Cable,
  Check,
  CircleHelp,
  Piano,
  RefreshCw,
  SlidersHorizontal,
  Upload,
} from "lucide-react";
import React from "react";
import { TouchButton } from "../TouchButton";
import { api, json, type Session, type Settings } from "../api";
import type { Status } from "../appTypes";

type Props = {
  settings: Settings;
  setSettings: React.Dispatch<React.SetStateAction<Settings>>;
  status: Status | null;
  run: (action: () => Promise<unknown>) => Promise<void>;
  busy: boolean;
  midiImport: React.RefObject<HTMLInputElement | null>;
  sessions: Session[];
  saveSettings: () => Promise<void>;
};

export function SettingsDialog({
  settings,
  setSettings,
  status,
  run,
  busy,
  midiImport,
  sessions,
  saveSettings,
}: Props) {
  return (
    <>
      <div className="settings-section">
        <h3>
          <Cable size={21} />
          MIDI connection
        </h3>
        <label>
          Preferred device name (stable portion)
          <input
            placeholder="e.g. CASIO or AP-470"
            value={settings.preferred_device}
            onChange={(e) =>
              setSettings({
                ...settings,
                preferred_device: e.target.value,
              })
            }
          />
        </label>
        <p className="muted">
          Casio devices connect automatically. Choose a detected device to
          prefill its identity.
        </p>
        <div className="device-list">
          {status?.devices.length ? (
            status.devices.map((d) => (
              <TouchButton
                key={d}
                className="secondary"
                onClick={() =>
                  setSettings({
                    ...settings,
                    preferred_device: d.replace(/\s+\d+:\d+$/, ""),
                  })
                }
              >
                {d}
              </TouchButton>
            ))
          ) : (
            <p>
              No MIDI input detected. Connect the USB Type-B cable and switch on
              the piano.
            </p>
          )}
        </div>
        {status?.device_error && (
          <p className="warning-text">{status.device_error}</p>
        )}
        <TouchButton
          className="secondary"
          onClick={() =>
            void run(() => api("/devices/reconnect", { method: "POST" }))
          }
        >
          <RefreshCw size={18} />
          Reconnect now
        </TouchButton>
        <div className="pedal-values">
          {[64, 66, 67].map((cc, i) => (
            <div key={cc}>
              <span>
                {["Damper", "Sostenuto", "Soft"][i]} · CC{cc}
              </span>
              <strong>
                {status?.pedals[cc] || 0}
                <small> / 127</small>
              </strong>
              <meter min="0" max="127" value={status?.pedals[cc] || 0} />
            </div>
          ))}
        </div>
        <div className="diagnostics">
          <span>
            Held notes:{" "}
            {Object.entries(status?.notes || {})
              .map(([note, v]) => `${note.split(":")[1]} (v${v})`)
              .join(", ") || "none"}
          </span>
          <span>
            Rate: {status?.event_rate || 0} events/s · Queue:{" "}
            {status?.queue_depth || 0} · Last input:{" "}
            {status?.last_event_age == null
              ? "none"
              : status.last_event_age.toFixed(1) + " s ago"}
          </span>
        </div>
        <details>
          <summary>Recent MIDI messages</summary>
          <div className="event-log">
            {status?.recent
              .slice()
              .reverse()
              .map((e, i) => (
                <code key={i}>{e.message}</code>
              ))}
          </div>
        </details>
      </div>
      <div className="settings-section">
        <h3>
          <SlidersHorizontal size={21} />
          Touch & score controls
        </h3>
        {(
          [
            ["swipe", "Swipe to turn pages at fit scale"],
            ["pinch", "Pinch to zoom; drag to pan when zoomed"],
            ["double_tap", "Double tap to toggle fit / enlarged view"],
            ["tap_overlay", "Single tap to show / hide practice controls"],
            ["auto_hide", "Hide controls after 10 seconds of recording"],
            ["pedal_enabled", "Enable pedal page turning"],
          ] as const
        ).map(([key, label]) => (
          <label className="toggle-row" key={key}>
            <span>{label}</span>
            <input
              type="checkbox"
              checked={settings[key]}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  [key]: e.target.checked,
                })
              }
            />
          </label>
        ))}
        <label>
          Page-turn pedal controller
          <select
            value={settings.pedal_controller ?? 66}
            onChange={(e) =>
              setSettings({
                ...settings,
                pedal_controller: Number(e.target.value),
              })
            }
          >
            <option value={66}>Middle / sostenuto · CC66</option>
            <option value={67}>Soft · CC67</option>
            <option value={64}>Damper pedal (CC64)</option>
          </select>
        </label>
        <label>
          Piece separation cooldown (seconds)
          <input
            type="number"
            min={5}
            max={300}
            value={settings.separation_cooldown ?? 20}
            onChange={(e) =>
              setSettings({
                ...settings,
                separation_cooldown: Number(e.target.value),
              })
            }
          />
        </label>
        <div className="info-box">
          <CircleHelp size={20} />
          <p>
            Pedal page control is disabled by default. Select the controller
            that moves in the device readout. The selected pedal's musical
            function still sounds on the piano. is the usual middle pedal. Test:
            single press → next, double press → previous, hold over 0.8 s →
            controls. This does not disable the piano’s internal sostenuto. Raw
            pedal data is always recorded; command interpretation is tagged in
            the journal. Keyboard arrows or an external USB pedal are
            alternatives. Learning has its own middle-pedal repeat control; it
            does not use that pedal to turn pages.
          </p>
        </div>
      </div>
      <div className="settings-section">
        <h3>
          <Piano size={21} />
          Simulation & installation check
        </h3>
        <p>
          Feed a synthetic scale or saved MIDI through the same recorder input.
          Simulated performances are marked in the journal. No hardware
          validation is implied.
        </p>
        <div className="button-row">
          <TouchButton
            className="secondary"
            disabled={busy}
            onClick={() =>
              void run(() =>
                api(
                  status?.simulation ? "/simulation/stop" : "/simulation/start",
                  status?.simulation ? { method: "POST" } : json("POST", {}),
                ),
              )
            }
          >
            {status?.simulation ? "Stop simulation" : "Play synthetic scale"}
          </TouchButton>
          <TouchButton
            className="secondary"
            onClick={() => midiImport.current?.click()}
          >
            <Upload size={18} />
            Import MIDI / CSV
          </TouchButton>
        </div>
        <select
          aria-label="Replay imported session"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value)
              void run(() =>
                api(
                  "/simulation/start",
                  json("POST", {
                    session_id: e.target.value,
                    speed: 1,
                  }),
                ),
              );
            e.target.value = "";
          }}
        >
          <option value="">Replay a saved recording as input…</option>
          {sessions
            .filter((s) => s.status !== "recording")
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
        </select>
        <p className="muted">
          Simulation produces MIDI input, not sound. Request optional audio
          rendering from a saved activity in session review.
        </p>
      </div>
      <div className="modal-actions">
        <TouchButton
          className="primary"
          disabled={busy}
          onClick={() => void saveSettings()}
        >
          <Check size={18} />
          Save settings
        </TouchButton>
      </div>
    </>
  );
}
