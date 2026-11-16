import { useEffect, useState } from "react";
import { api, json } from "./api";
import { TouchButton as Button } from "./TouchButton";

import type { PassageData, PassagePoint } from "./types/passages";
export type { PassageData, PassagePoint } from "./types/passages";
const metrics = [
  ["bpm", "Local tempo · ♩/min"],
  ["velocity", "Attack velocity · 7-bit scale"],
  ["melody_velocity", "Melody dynamics · velocity proxy"],
  ["bass_velocity", "Bass dynamics · velocity proxy"],
  ["inner_velocity", "Inner-voice dynamics · velocity proxy"],
  ["duration_ratio", "Key duration / score duration"],
  ["pedal", "Pedal CC64 · 0–127"],
  ["release_velocity", "Release velocity · raw 7-bit"],
] as const;
const display = (n: number | null | undefined, digits = 1) =>
  n == null ? "—" : n.toFixed(digits);

export function PassageComparison({
  data,
  second,
  beats,
  onSelect,
  selectedBeat,
  pieceId,
  onError,
}: {
  data?: PassageData;
  second?: PassageData;
  beats?: number[];
  onSelect?: (p: PassagePoint) => void;
  selectedBeat?: number;
  pieceId?: string;
  onError?: (e: unknown) => void;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const [target, setTarget] = useState<PassageData["target"]>({});
  const [message, setMessage] = useState("");
  useEffect(() => {
    setTarget(data?.target || {});
    setSelected(null);
    setMessage("");
  }, [data]);
  if (!data?.points.length)
    return <p>Analyse again to create synchronized passage measurements.</p>;
  const dynamics = (p: PassagePoint): PassagePoint => ({
    ...p,
    melody_velocity: p.voices.melody ?? null,
    bass_velocity: p.voices.bass ?? null,
    inner_velocity: p.voices.inner ?? null,
  });
  const points = data.points
    .filter((p) => !beats || beats.includes(p.beat))
    .map(dynamics);
  const bIndex = new Map(
    second?.points.map((p) => [`${p.measure}:${p.beat}`, dynamics(p)]),
  );
  const lanes = metrics.filter(
    ([key]) =>
      !["melody_velocity", "bass_velocity", "inner_velocity"].includes(key) ||
      points.some((p) => p[key] != null) ||
      [...bIndex.values()].some((p) => p[key] != null),
  );
  const chosen =
    points.find((p) =>
      selectedBeat != null ? p.beat === selectedBeat : p.index === selected,
    ) || points[0];
  const choose = (p: PassagePoint) => {
    setSelected(p.index);
    onSelect?.(p);
  };
  const minBeat = Math.min(...points.map((p) => p.beat)),
    maxBeat = Math.max(...points.map((p) => p.beat));
  const x = (p: PassagePoint) =>
    65 + (690 * (p.beat - minBeat)) / Math.max(1, maxBeat - minBeat);
  return (
    <section
      className="passage-comparison"
      aria-label="Synchronized passage measurements"
    >
      <h3>Synchronized passage measurements</h3>
      <p>{data.notice}</p>
      {!data.trusted && (
        <p className="info-box">
          Alignment or capture needs review. Measurements are descriptive;
          correctness checks are withheld.
        </p>
      )}
      <p>
        First attempt: solid green
        {second ? " · Second attempt: dashed purple" : ""}. All lanes use the
        same score-beat axis. Dynamics markings appear in the table.
      </p>
      <div className="note-overlay-scroll">
        <svg
          viewBox={`0 0 800 ${lanes.length * 75 + 30}`}
          style={{ minWidth: 650, width: "100%", maxWidth: 1100 }}
          role="img"
          aria-label="Tempo, voice dynamics, velocity, duration, pedal and release aligned to score beats"
        >
          {lanes.map(([key, label], lane) => {
            const values = [
              ...points,
              ...(second?.points
                .map(dynamics)
                .filter((p) =>
                  points.some(
                    (a) => a.measure === p.measure && a.beat === p.beat,
                  ),
                ) || []),
            ]
              .map((p) => p[key])
              .filter((v): v is number => v != null);
            const low =
              key === "pedal" ||
              key === "velocity" ||
              key === "release_velocity" ||
              key.endsWith("velocity")
                ? 0
                : Math.min(0, ...values);
            const high =
              key === "pedal" ||
              key === "velocity" ||
              key === "release_velocity" ||
              key.endsWith("velocity")
                ? 128
                : Math.max(1, ...values);
            const y = (value: number) =>
              lane * 75 + 62 - (35 * (value - low)) / (high - low);
            const line = (ps: (PassagePoint | undefined)[]) => {
              let connected = false;
              return ps
                .map((p) => {
                  if (!p || p[key] == null || p.time == null) {
                    connected = false;
                    return "";
                  }
                  const d = `${connected ? "L" : "M"}${x(p)},${y(p[key] as number)}`;
                  connected = true;
                  return d;
                })
                .join(" ");
            };
            return (
              <g key={key}>
                <text x="12" y={lane * 75 + 16}>
                  {label}
                </text>
                <text x="12" y={lane * 75 + 32}>
                  {display(high)}
                </text>
                <line
                  x1="65"
                  x2="755"
                  y1={lane * 75 + 62}
                  y2={lane * 75 + 62}
                  stroke="#b9b6ab"
                />
                {!values.length && (
                  <text x="320" y={lane * 75 + 46}>
                    No measurements at these score positions
                  </text>
                )}
                <path
                  d={line(points)}
                  fill="none"
                  stroke="#397858"
                  strokeWidth="2"
                />
                {second && (
                  <path
                    d={line(
                      points.map((p) => bIndex.get(`${p.measure}:${p.beat}`)),
                    )}
                    fill="none"
                    stroke="#8254a1"
                    strokeWidth="2"
                    strokeDasharray="6 4"
                  />
                )}
                {points
                  .filter((p) => p[key] != null && p.time != null)
                  .map((p) => (
                    <circle
                      key={p.index}
                      cx={x(p)}
                      cy={y(p[key] as number)}
                      r="3"
                      fill="#397858"
                    />
                  ))}
                {chosen && (
                  <line
                    x1={x(chosen)}
                    x2={x(chosen)}
                    y1={lane * 75 + 24}
                    y2={lane * 75 + 66}
                    stroke="#a46b21"
                  />
                )}
              </g>
            );
          })}
          {points
            .filter(
              (p, i) => i % Math.max(1, Math.ceil(points.length / 12)) === 0,
            )
            .map((p) => (
              <text
                key={p.index}
                x={x(p)}
                y={lanes.length * 75 + 15}
                textAnchor="middle"
              >
                m{p.measure ?? "?"} · {display(p.beat)}
              </text>
            ))}
        </svg>
      </div>
      <div className="passage-table-scroll">
        <table>
          <thead>
            <tr>
              <th>Score location</th>
              <th>Session seconds</th>
              <th>Tempo</th>
              <th>Velocity / dynamics</th>
              <th>Duration ratio</th>
              <th>Pedal</th>
              <th>Release</th>
              <th>Differences</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => {
              const b = bIndex.get(`${p.measure}:${p.beat}`);
              const cell = (key: (typeof metrics)[number][0]) => (
                <>
                  {display(p[key])}
                  {second && <> / {display(b?.[key])}</>}
                </>
              );
              return (
                <tr key={p.index} aria-selected={chosen?.index === p.index}>
                  <td>
                    <Button className="secondary" onClick={() => choose(p)}>
                      m{p.measure ?? "?"} · beat {display(p.beat, 2)}
                    </Button>
                  </td>
                  <td>
                    {display(p.time, 3)}
                    {second && <> / {display(b?.time, 3)}</>}
                  </td>
                  <td>{cell("bpm")}</td>
                  <td>
                    {cell("velocity")} · {p.dynamics.join(", ") || "No marking"}
                  </td>
                  <td>{cell("duration_ratio")}</td>
                  <td>{cell("pedal")}</td>
                  <td>{cell("release_velocity")}</td>
                  <td>
                    −{p.missing.length} / +{p.extra.length}
                    {b && (
                      <>
                        ; second −{b.missing.length} / +{b.extra.length}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {chosen && (
        <div className="info-box">
          <strong>
            Measure {chosen.measure ?? "?"}, score beat{" "}
            {display(chosen.beat, 2)}
          </strong>
          <p>
            Voice balance:{" "}
            {Object.entries(chosen.voices)
              .map(([role, value]) => `${role} ${display(value)}`)
              .join(" · ") || "Assign score voices below to evaluate balance."}
          </p>
          {chosen.voicing.map((v) => (
            <p key={v.against}>
              Melody minus {v.against}: {display(v.melody_gap)} ·{" "}
              {v.status.replaceAll("_", " ")}
            </p>
          ))}
          {!!chosen.pedal_changes?.length && (
            <p>
              Pedal changes after this attack:{" "}
              {chosen.pedal_changes
                .map(
                  (e) =>
                    `${display(e.time, 3)} s / channel ${e.channel + 1}: ${e.value}`,
                )
                .join(" · ")}
            </p>
          )}
          <details>
            <summary>Individual note measurements</summary>
            {chosen.notes.map((n, i) => (
              <p key={i}>
                MIDI {n.pitch} · voice {n.voice_key || "ambiguous"}{" "}
                {n.role || ""} · attack {n.velocity ?? "—"} / 14-bit{" "}
                {n.velocity_14 ?? "unavailable"} · release{" "}
                {n.release_velocity ?? "unavailable"} / 14-bit{" "}
                {n.release_velocity_14 ?? "unavailable"} · held{" "}
                {display(n.duration, 3)} s · duration ratio{" "}
                {display(n.duration_ratio)} · pedal {n.pedal ?? "unknown"}
              </p>
            ))}
          </details>
        </div>
      )}
      {chosen && second && (
        <details>
          <summary>Second attempt at selected score position</summary>
          {bIndex.get(`${chosen.measure}:${chosen.beat}`)?.notes.map((n, i) => (
            <p key={i}>
              MIDI {n.pitch} · {n.role || n.voice_key || "unassigned"} · attack{" "}
              {n.velocity ?? "—"} / 14-bit {n.velocity_14 ?? "unavailable"} ·
              release {n.release_velocity ?? "unavailable"} / 14-bit{" "}
              {n.release_velocity_14 ?? "unavailable"} · held{" "}
              {display(n.duration, 3)} s · duration ratio{" "}
              {display(n.duration_ratio)} · pedal {n.pedal ?? "unknown"}
            </p>
          ))}
        </details>
      )}
      <details>
        <summary>
          Passage voice balance, including non-simultaneous attacks
        </summary>
        <p>
          Measure averages complement the simultaneous-onset check. Compare the
          same voice roles and phrase context; velocity does not establish
          acoustic loudness.
        </p>
        {data.measures
          ?.filter((m) => points.some((p) => p.measure === m.measure))
          .map((m, i) => (
            <p key={i}>
              Measure {m.measure ?? "?"}:{" "}
              {Object.entries(m.voices)
                .map(([role, value]) => `${role} ${display(value)}`)
                .join(" · ") || "No assigned roles"}
              {m.voicing
                .map(
                  (v) =>
                    ` · melody minus ${v.against} ${display(v.melody_gap)} (${v.status.replaceAll("_", " ")})`,
                )
                .join("")}
              {second && (
                <>
                  {" "}
                  · second:{" "}
                  {Object.entries(
                    second.measures?.find((b) => b.measure === m.measure)
                      ?.voices || {},
                  )
                    .map(([role, value]) => `${role} ${display(value)}`)
                    .join(" · ") || "No assigned roles"}
                </>
              )}
            </p>
          ))}
      </details>
      <p>
        Release data: {data.release.status.replaceAll("_", " ")} ·{" "}
        {data.release.count} note-offs · {data.release.distinct_values} distinct
        values. {data.release.notice}
      </p>
      {pieceId && (
        <details>
          <summary>Voice roles, dynamics target & release calibration</summary>
          <p>
            Assign source part:staff:voice identities from your edition. Staff
            and pitch register alone cannot establish the melody. The melody
            margin is a chosen MIDI-velocity practice target, not a universal
            balance rule. Save, then analyse again.
          </p>
          <div className="form-grid">
            {data.voices.map((voice) => (
              <label key={voice}>
                Voice {voice}
                <select
                  value={target.roles?.[voice] || "unassigned"}
                  onChange={(e) =>
                    setTarget({
                      ...target,
                      roles: { ...target.roles, [voice]: e.target.value },
                    })
                  }
                >
                  {["unassigned", "bass", "inner", "melody"].map((role) => (
                    <option key={role}>{role}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <label>
            Minimum melody velocity above accompaniment
            <input
              type="number"
              min="-127"
              max="127"
              value={target.melody_min_gap ?? ""}
              onChange={(e) =>
                setTarget({
                  ...target,
                  melody_min_gap:
                    e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </label>
          <label className="toggle-row">
            I have calibrated release velocity for this device/tone
            <input
              type="checkbox"
              checked={!!target.release_calibrated}
              onChange={(e) =>
                setTarget({ ...target, release_calibrated: e.target.checked })
              }
            />
          </label>
          <Button
            className="secondary"
            onClick={() =>
              void api(`/pieces/${pieceId}/voicing`, json("PUT", target))
                .then(() =>
                  setMessage(
                    "Saved. Analyse the activity again to apply these targets.",
                  ),
                )
                .catch(onError || (() => setMessage("Could not save targets.")))
            }
          >
            Save analysis targets
          </Button>
          {message && <p role="status">{message}</p>}
        </details>
      )}
    </section>
  );
}
