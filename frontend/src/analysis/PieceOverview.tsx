import { useState } from "react";
import type { PassageData, PassagePoint } from "../types/passages";
import { TouchButton as Button } from "../TouchButton";

const laneHeight = 180;
const plotTop = 40;
const plotBottom = 155;

const metrics = [
  { key: "bpm", label: "Local tempo · BPM (♩/min)", fixed: false },
  { key: "velocity", label: "Attack velocity · 0–127", fixed: true },
  { key: "melody", label: "Melody velocity proxy · 0–127", fixed: true },
  { key: "bass", label: "Bass velocity proxy · 0–127", fixed: true },
  { key: "inner", label: "Inner-voice velocity proxy · 0–127", fixed: true },
  {
    key: "duration_ratio",
    label: "Key duration / score duration",
    fixed: false,
  },
  { key: "pedal", label: "Pedal CC64 · 0–127", fixed: true },
  {
    key: "release_velocity",
    label: "Release velocity · raw 0–127",
    fixed: true,
  },
] as const;
type Metric = (typeof metrics)[number]["key"];
const value = (point: PassagePoint, key: Metric) =>
  key === "melody" || key === "bass" || key === "inner"
    ? point.voices[key]
    : point[key];

export function PieceOverview({
  data,
  onMeasure,
}: {
  data?: PassageData;
  onMeasure: (measure: number) => void;
}) {
  const [scale, setScale] = useState(1);
  const [start, setStart] = useState(0);
  const [enabled, setEnabled] = useState<Metric[]>([
    "bpm",
    "velocity",
    "pedal",
  ]);
  const located = data?.points.filter((p) => p.measure != null) || [];
  if (!located.length)
    return (
      <section aria-label="Whole-piece overview">
        <h3>Whole-piece overview</h3>
        <p>
          Analyse this activity again with a measure-labelled reference to
          create the overview.
        </p>
      </section>
    );
  const byMeasure = new Map<number, PassagePoint[]>();
  for (const point of located) {
    const measure = point.measure!;
    if (!byMeasure.has(measure)) byMeasure.set(measure, []);
    byMeasure.get(measure)!.push(point);
  }
  const labels = [...byMeasure.keys()].sort((a, b) => a - b);
  const first = labels[0],
    last = labels[labels.length - 1];
  const count = last - first + 1;
  const span = Math.max(1, Math.ceil(count / scale));
  const offset = Math.min(start, count - span);
  const from = first + offset,
    to = from + span - 1;
  const lanes = metrics.filter((metric) => enabled.includes(metric.key));
  const x = (measure: number) => 95 + ((measure - from + 0.5) / span) * 1080;
  const selected = Array.from({ length: span }, (_, i) => from + i);
  const tickStep = Math.max(1, Math.ceil(span / 12));
  return (
    <section className="piece-overview" aria-label="Whole-piece overview">
      <h3>Whole-piece overview</h3>
      <p>
        All saved analysis coverage: measures {first}–{last}. A partial take
        covers only its analysed region. Each point is a measure mean; vertical
        strokes show its minimum–maximum range. Measures have equal width. Gaps
        mean unavailable measurements. Tap a measure to review it below.
      </p>
      {!data?.trusted && (
        <p className="info-box">
          Alignment or capture needs review. These measurements are descriptive
          estimates.
        </p>
      )}
      <div className="button-row">
        <label>
          Overview scale
          <select
            value={scale}
            onChange={(e) => {
              setScale(Number(e.target.value));
              setStart(0);
            }}
          >
            <option value={1}>Whole piece</option>
            <option value={2}>Half piece</option>
            <option value={4}>Quarter piece</option>
          </select>
        </label>
        <Button
          className="secondary"
          disabled={offset === 0}
          onClick={() => setStart(Math.max(0, offset - span))}
        >
          Earlier measures
        </Button>
        <Button
          className="secondary"
          disabled={offset + span >= count}
          onClick={() => setStart(Math.min(count - span, offset + span))}
        >
          Later measures
        </Button>
        <span role="status">
          Showing measures {from}–{to}
        </span>
      </div>
      {scale > 1 && (
        <label>
          First overview measure
          <input
            type="range"
            min={0}
            max={count - span}
            value={offset}
            onChange={(e) => setStart(Number(e.target.value))}
          />
        </label>
      )}
      <fieldset className="overview-metrics">
        <legend>Chart measurements</legend>
        {metrics.map((metric) => (
          <label key={metric.key}>
            <input
              type="checkbox"
              checked={enabled.includes(metric.key)}
              onChange={(e) =>
                setEnabled(
                  e.target.checked
                    ? [...enabled, metric.key]
                    : enabled.filter((key) => key !== metric.key),
                )
              }
            />
            {metric.label}
          </label>
        ))}
      </fieldset>
      {!lanes.length ? (
        <p>Select a measurement to display.</p>
      ) : (
        <svg
          className="overview-chart"
          viewBox={`0 0 1200 ${lanes.length * laneHeight + 45}`}
          role="group"
          aria-label={`Whole-piece measurements, measures ${from}–${to}`}
        >
          {lanes.map((metric, lane) => {
            const summary = (measure: number) => {
              const values = (byMeasure.get(measure) || [])
                .filter((p) => p.time != null)
                .map((p) => value(p, metric.key))
                .filter((v): v is number => v != null && Number.isFinite(v));
              return values.length
                ? {
                    mean: values.reduce((a, b) => a + b, 0) / values.length,
                    min: Math.min(...values),
                    max: Math.max(...values),
                  }
                : null;
            };
            // Keep the scale stable while panning between ranges.
            const all = labels.map(summary).filter((v) => v != null);
            const maximum = Math.max(1, ...all.map((v) => v.max));
            const roughStep = maximum / 4;
            const magnitude = 10 ** Math.floor(Math.log10(roughStep));
            const step = Math.ceil(roughStep / magnitude) * magnitude;
            const high = metric.fixed ? 127 : Math.ceil(maximum / step) * step;
            const ticks = metric.fixed
              ? [0, 32, 64, 96, 127]
              : Array.from(
                  { length: Math.round(high / step) + 1 },
                  (_, i) => i * step,
                );
            const y = (v: number) =>
              lane * laneHeight +
              plotBottom -
              (v / high) * (plotBottom - plotTop);
            const tickLabel = (v: number) =>
              metric.key === "bpm"
                ? `${Number(v.toFixed(2))} BPM`
                : String(Number(v.toFixed(2)));
            let connected = false;
            const path = selected
              .map((m) => {
                const stats = summary(m);
                if (!stats) {
                  connected = false;
                  return "";
                }
                const command = `${connected ? "L" : "M"}${x(m)},${y(stats.mean)}`;
                connected = true;
                return command;
              })
              .join(" ");
            return (
              <g key={metric.key} aria-label={`${metric.label} chart`}>
                <text x={10} y={lane * laneHeight + 20}>
                  {metric.label}
                </text>
                {ticks.map((tick) => (
                  <g key={tick} className="overview-y-tick">
                    <text
                      x={85}
                      y={y(tick)}
                      textAnchor="end"
                      dominantBaseline="middle"
                    >
                      {tickLabel(tick)}
                    </text>
                    <line
                      x1={95}
                      x2={1175}
                      y1={y(tick)}
                      y2={y(tick)}
                      stroke="#b9b6ab"
                      strokeOpacity={tick === 0 ? 1 : 0.45}
                    />
                  </g>
                ))}
                <path d={path} fill="none" stroke="#397858" strokeWidth={2} />
                {selected.map((m) => {
                  const stats = summary(m);
                  return (
                    stats && (
                      <g key={m}>
                        <title>
                          {`Measure ${m}: mean ${stats.mean.toFixed(1)}, range ${stats.min.toFixed(1)}–${stats.max.toFixed(1)}${metric.key === "bpm" ? " BPM" : ""}`}
                        </title>
                        <line
                          x1={x(m)}
                          x2={x(m)}
                          y1={y(stats.min)}
                          y2={y(stats.max)}
                          stroke="#397858"
                          opacity={0.45}
                          strokeWidth={3}
                        />
                        <circle
                          cx={x(m)}
                          cy={y(stats.mean)}
                          r={3}
                          fill="#397858"
                        />
                      </g>
                    )
                  );
                })}
                {!all.length && (
                  <text x={400} y={lane * laneHeight + 100}>
                    No measurements available
                  </text>
                )}
              </g>
            );
          })}
          {selected.map((m, i) => (
            <g key={m}>
              {((i % tickStep === 0 && i < span - tickStep / 2) ||
                i === span - 1) && (
                <text
                  x={x(m)}
                  y={lanes.length * laneHeight + 20}
                  textAnchor="middle"
                >
                  m{m}
                </text>
              )}
              <rect
                x={95 + (i / span) * 1080}
                y={25}
                width={1080 / span}
                height={lanes.length * laneHeight - 25}
                fill="transparent"
                role="button"
                tabIndex={0}
                aria-label={`Review measure ${m}`}
                onClick={() => onMeasure(m)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onMeasure(m);
                  }
                }}
              >
                <title>{`Review measure ${m}`}</title>
              </rect>
            </g>
          ))}
        </svg>
      )}
      <p className="muted">
        Local tempo and alignment are estimates. MIDI velocity is a dynamics
        proxy, not acoustic loudness; release velocity needs device calibration.
        Unknown score locations are omitted.
      </p>
    </section>
  );
}
