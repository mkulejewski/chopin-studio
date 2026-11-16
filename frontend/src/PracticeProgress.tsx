import { useState } from "react";
import { api, clock, json } from "./api";
import { TouchButton as Button } from "./TouchButton";
import type { PerformanceTake } from "./types/practice";
import type { ProgressPiece } from "./types/progress";

export function PracticeProgress({
  piece,
  reload,
  onError,
}: {
  piece: ProgressPiece;
  reload: () => Promise<void>;
  onError: (e: unknown) => void;
}) {
  const [open, setOpen] = useState(false),
    [takes, setTakes] = useState<PerformanceTake[]>([]);
  const [title, setTitle] = useState(""),
    [category, setCategory] = useState("tempo");
  const [first, setFirst] = useState(""),
    [last, setLast] = useState("");
  const [objective, setObjective] = useState(""),
    [take, setTake] = useState("");
  const [start, setStart] = useState(0),
    [end, setEnd] = useState(0),
    [busy, setBusy] = useState(false);
  const data = piece.practice;
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await reload();
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <details
      className="progress-details"
      open={open}
      onToggle={(e) => {
        const value = e.currentTarget.open;
        setOpen(value);
        if (value && !takes.length)
          void api<PerformanceTake[]>("/performances")
            .then((rows) =>
              setTakes(rows.filter((t) => t.piece_id === piece.id)),
            )
            .catch(onError);
      }}
    >
      <summary>
        Measures, recurring mistakes, recall & technical objectives ·{" "}
        {piece.title} {piece.opus}
      </summary>
      {open && (
        <>
          <p>{data?.notice}</p>
          <h4>Measure-level progress</h4>
          <div className="passage-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Measure / reference</th>
                  <th>Analysed attempts</th>
                  <th>Located time</th>
                  <th>Latest missing / extra</th>
                  <th>Recent history</th>
                </tr>
              </thead>
              <tbody>
                {data?.measures?.map((m) => (
                  <tr
                    key={`${m.reference_id}:${m.reference_revision}:${m.measure}`}
                  >
                    <td>
                      {m.measure} · {m.reference_id?.slice(0, 8)} /{" "}
                      {m.reference_revision?.slice(0, 6)}
                    </td>
                    <td>{m.attempts}</td>
                    <td>{clock(m.seconds)}</td>
                    <td>
                      {m.latest.missing} / {m.latest.extra}
                    </td>
                    <td>
                      {m.history.slice(-5).map((h, i: number) => (
                        <span key={i}>
                          {h.date.slice(0, 10)}: −{h.missing}/+{h.extra}
                          {h.trusted ? "" : " (review)"}
                          {" · "}
                        </span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data?.measures?.length && (
            <p>
              No current passage analysis. Analyse identified activities to
              build measure history.
            </p>
          )}
          <h4>Recurring differences to review</h4>
          <ul>
            {data?.recurring_mistakes?.map((m, i: number) => (
              <li key={i}>
                Measure {m.measure}: {m.kind.replaceAll("_", " ")} MIDI{" "}
                {m.pitch} · {m.attempts} distinct attempts · last{" "}
                {m.history.at(-1)?.date.slice(0, 10)}
              </li>
            ))}
          </ul>
          {!data?.recurring_mistakes?.length && (
            <p>No repeated discrepancy recorded in current analyses.</p>
          )}
          <h4>Memorization retention</h4>
          {data?.retention?.map((r, i: number) => (
            <p key={i}>
              Measures {r.first_measure}–{r.last_measure} · {r.hand} ·{" "}
              {r.passes}/{r.tests} unassisted recall tests passed · last{" "}
              {r.days_since_test ?? "?"} days ago (
              {r.last_passed
                ? "passed"
                : r.last_manual_accepted
                  ? "remembered by self-assessment"
                  : "needs review"}
              ) · longest successful retest gap{" "}
              {r.longest_successful_gap_days ?? "not established"} days
              {r.review_due ? " · review due" : ""} ·{" "}
              {r.manual_recollections || 0} self-assessed recollections · note
              rules {r.note_rules} · reference revision{" "}
              {r.revision.slice(0, 12)}
            </p>
          ))}
          {!data?.retention?.length && (
            <p>
              No eligible unassisted Learning recall tests yet. Ordinary
              score-visible practice does not demonstrate memorization.
            </p>
          )}
          <h4>Technical objectives & musical problems</h4>
          {data?.objectives?.map((o) => (
            <div className="info-box" key={o.id}>
              <strong>{o.title}</strong> · {o.category} · measures{" "}
              {o.first_measure ?? "?"}–{o.last_measure ?? "?"} ·{" "}
              {clock(o.seconds)} explicitly attributed
              <label className="toggle-row">
                Completed
                <input
                  type="checkbox"
                  checked={!!o.completed}
                  disabled={busy}
                  onChange={(e) =>
                    void run(() =>
                      api(
                        `/objectives/${o.id}`,
                        json("PUT", { ...o, completed: e.target.checked }),
                      ),
                    )
                  }
                />
              </label>
              <details>
                <summary>Edit objective and attributed intervals</summary>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    void run(() =>
                      api(
                        `/objectives/${o.id}`,
                        json("PUT", {
                          ...o,
                          title: String(f.get("title")),
                          category: String(f.get("category")),
                          first_measure: f.get("first")
                            ? Number(f.get("first"))
                            : null,
                          last_measure: f.get("last")
                            ? Number(f.get("last"))
                            : null,
                        }),
                      ),
                    );
                  }}
                >
                  <label>
                    Objective
                    <input
                      name="title"
                      required
                      maxLength={200}
                      defaultValue={o.title}
                    />
                  </label>
                  <label>
                    Skill
                    <select name="category" defaultValue={o.category}>
                      {[
                        "tempo",
                        "rhythm",
                        "voicing",
                        "dynamics",
                        "articulation",
                        "pedal",
                        "memory",
                        "other",
                      ].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    First measure
                    <input
                      name="first"
                      type="number"
                      min="0"
                      defaultValue={o.first_measure ?? ""}
                    />
                  </label>
                  <label>
                    Last measure
                    <input
                      name="last"
                      type="number"
                      min="0"
                      defaultValue={o.last_measure ?? ""}
                    />
                  </label>
                  <Button disabled={busy} className="secondary" type="submit">
                    Save objective
                  </Button>
                </form>
                {o.attributions?.map((t) => (
                  <p key={t.id}>
                    Session {t.session_id.slice(0, 8)} · {clock(t.start)}–
                    {clock(t.end)}{" "}
                    <Button
                      disabled={busy}
                      className="secondary"
                      onClick={() =>
                        void run(() =>
                          api(`/objectives/${o.id}/time/${t.id}`, {
                            method: "DELETE",
                          }),
                        )
                      }
                    >
                      Remove attribution
                    </Button>
                  </p>
                ))}
              </details>
            </div>
          ))}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                await api(
                  `/pieces/${piece.id}/objectives`,
                  json("POST", {
                    title,
                    category,
                    first_measure: first === "" ? null : Number(first),
                    last_measure: last === "" ? null : Number(last),
                  }),
                );
                setTitle("");
              });
            }}
          >
            <div className="form-grid">
              <label>
                New objective
                <input
                  required
                  maxLength={200}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label>
                Skill
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {[
                    "tempo",
                    "rhythm",
                    "voicing",
                    "dynamics",
                    "articulation",
                    "pedal",
                    "memory",
                    "other",
                  ].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label>
                First measure
                <input
                  type="number"
                  min="0"
                  value={first}
                  onChange={(e) => setFirst(e.target.value)}
                />
              </label>
              <label>
                Last measure
                <input
                  type="number"
                  min="0"
                  value={last}
                  onChange={(e) => setLast(e.target.value)}
                />
              </label>
            </div>
            <Button className="secondary" disabled={busy} type="submit">
              Add technical objective
            </Button>
          </form>
          <h4>Attribute recorded time to a problem</h4>
          <div className="form-grid">
            <label>
              Objective
              <select
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              >
                <option value="">Choose objective</option>
                {data?.objectives?.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Activity
              <select
                value={take}
                onChange={(e) => {
                  setTake(e.target.value);
                  const t = takes.find((t) => t.id === e.target.value);
                  setStart(t?.start || 0);
                  setEnd(t?.end || 0);
                }}
              >
                <option value="">Choose recorded activity</option>
                {takes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.started.slice(0, 10)} · {clock(t.start)}–{clock(t.end)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Start seconds
              <input
                type="number"
                min="0"
                step=".001"
                value={start}
                onChange={(e) => setStart(Number(e.target.value))}
              />
            </label>
            <label>
              End seconds
              <input
                type="number"
                min="0"
                step=".001"
                value={end}
                onChange={(e) => setEnd(Number(e.target.value))}
              />
            </label>
          </div>
          <Button
            className="secondary"
            disabled={busy || !objective || !take || end <= start}
            onClick={() =>
              void run(() =>
                api(
                  `/objectives/${objective}/time`,
                  json("POST", { segment_id: take, start, end }),
                ),
              )
            }
          >
            Attribute interval
          </Button>
          <p>
            Overlapping intervals count once per objective. Piece totals include
            activity time; located measure time omits long pauses. Time can
            belong to more than one musical problem.
          </p>
        </>
      )}
    </details>
  );
}
