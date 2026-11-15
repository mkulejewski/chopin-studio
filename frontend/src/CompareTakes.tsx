import { PassageComparison } from "./PassageComparison";
import { ScoreComparison } from "./ScoreComparison";
import { useEffect, useState } from "react";
import { api, clock } from "./api";
import { TouchButton as Button } from "./TouchButton";
export function CompareTakes({ onError }: { onError: (e: unknown) => void }) {
  const [takes, setTakes] = useState<any[]>([]),
    [left, setLeft] = useState(""),
    [right, setRight] = useState(""),
    [result, setResult] = useState<any>(null),
    [page, setPage] = useState(0),
    [measure, setMeasure] = useState("all"),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    void api<any[]>("/performances").then(setTakes).catch(onError);
  }, []);
  const selected = takes.find((t) => t.id === left);
  const label = (t: any) =>
    `${t.title || t.piece_id || "Unknown"} · ${t.opus || ""} · ${new Date(t.started).toLocaleDateString()} ${clock(t.start)}–${clock(t.end)}`;
  const shared = (result?.aligned?.points || []).filter(
    (p: any) => measure === "all" || String(p.measure) === measure,
  );
  const sharedPage = shared.slice(page * 24, (page + 1) * 24);
  const pageBeats = sharedPage.map((p: any) => p.beat);
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
          <select
            value={right}
            onChange={(e) => {
              setRight(e.target.value);
              setResult(null);
            }}
          >
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
            .then((r) => {
              setResult(r);
              setPage(0);
              setMeasure("all");
            })
            .catch(onError)
            .finally(() => setBusy(false));
        }}
      >
        Compare measurements
      </Button>
      {result && (
        <>
          <p>{result.notice}</p>
          <p>{result.aligned?.notice}</p>
          <label>
            Compare measure
            <select
              value={measure}
              onChange={(e) => {
                setMeasure(e.target.value);
                setPage(0);
              }}
            >
              <option value="all">All shared measures</option>
              {[
                ...new Set<number>(
                  result.aligned?.points.map((p: any) => p.measure) || [],
                ),
              ].map((m) => (
                <option key={m} value={String(m)}>
                  Measure {m}
                </option>
              ))}
            </select>
          </label>
          {result.aligned?.status === "aligned" && (
            <>
              <p>
                {result.aligned.points.length} shared score positions. Values in
                the table are first / second.
              </p>
              <PassageComparison
                data={result.left.analysis.passages}
                second={result.right.analysis.passages}
                beats={pageBeats}
                pieceId={result.left.segment.piece_id}
                onError={onError}
              />
              <nav
                className="button-row"
                aria-label="Take comparison passage navigation"
              >
                <Button
                  className="secondary"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous passage
                </Button>
                <span>
                  Passage {page + 1} of{" "}
                  {Math.max(1, Math.ceil(shared.length / 24))}
                </span>
                <Button
                  className="secondary"
                  disabled={(page + 1) * 24 >= shared.length}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next passage
                </Button>
              </nav>
              {(["left", "right"] as const).map((side) => (
                <details key={side}>
                  <summary>
                    {side === "left" ? "First" : "Second"} attempt score
                    comparison
                  </summary>
                  <ScoreComparison
                    groups={(
                      result[side].analysis.note_comparison || []
                    ).filter((g: any) => pageBeats.includes(g.beat))}
                    allGroups={result[side].analysis.note_comparison || []}
                    mode="musical"
                    title={side === "left" ? "First attempt" : "Second attempt"}
                    fifths={result[side].analysis.key_fifths ?? 0}
                  />
                </details>
              ))}
            </>
          )}

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
