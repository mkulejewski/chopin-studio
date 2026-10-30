import { useEffect, useState } from "react";
import { api, clock } from "./api";
import { TouchButton as Button } from "./TouchButton";
export function CompareTakes({ onError }: { onError: (e: unknown) => void }) {
  const [takes, setTakes] = useState<any[]>([]),
    [left, setLeft] = useState(""),
    [right, setRight] = useState(""),
    [result, setResult] = useState<any>(null),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    void api<any[]>("/performances").then(setTakes).catch(onError);
  }, []);
  const selected = takes.find((t) => t.id === left);
  const label = (t: any) =>
    `${t.title || t.piece_id || "Unknown"} · ${t.opus || ""} · ${new Date(t.started).toLocaleDateString()} ${clock(t.start)}–${clock(t.end)}`;
  return (
    <div className="chart-panel">
      <h2>Compare two attempts</h2>
      <p>
        Choose identified activities from the same piece. Compare measurements
        and coverage; musical interpretation remains separate.
      </p>
      <div className="form-grid">
        <label>
          First attempt
          <select
            value={left}
            onChange={(e) => {
              setLeft(e.target.value);
              setRight("");
              setResult(null);
            }}
          >
            <option value="">Choose an activity</option>
            {takes
              .filter((t) => t.piece_id)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {label(t)}
                </option>
              ))}
          </select>
        </label>
        <label>
          Comparison attempt
          <select value={right} onChange={(e) => setRight(e.target.value)}>
            <option value="">Choose another activity</option>
            {takes
              .filter((t) => t.id !== left && t.piece_id === selected?.piece_id)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {label(t)}
                </option>
              ))}
          </select>
        </label>
      </div>
      <Button
        className="secondary"
        disabled={!left || !right || busy}
        onClick={() => {
          setBusy(true);
          void api(`/comparison?left=${left}&right=${right}`)
            .then(setResult)
            .catch(onError)
            .finally(() => setBusy(false));
        }}
      >
        Compare measurements
      </Button>
      {result && (
        <>
          <p>{result.notice}</p>
          <div className="metric-grid">
            {[
              ["left", "First attempt"],
              ["right", "Comparison attempt"],
            ].map(([key, title]) => (
              <div className="metric" key={key}>
                <span>{title}</span>
                <strong>{result[key].analysis.notes} notes</strong>
                <small>
                  Mean velocity{" "}
                  {result[key].analysis.velocity_mean?.toFixed(1) ?? "—"} ·
                  coverage {result[key].segment.first_measure ?? "?"}–
                  {result[key].segment.last_measure ?? "?"} measures
                </small>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
