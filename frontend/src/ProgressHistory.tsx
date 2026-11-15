import { PracticeProgress } from "./PracticeProgress";
import { TouchButton } from "./TouchButton";
import { useEffect, useState } from "react";
import { api, clock } from "./api";
export function ProgressHistory({
  onError,
}: {
  onError: (e: unknown) => void;
}) {
  const [rows, setRows] = useState<any[]>([]);
  const [days, setDays] = useState<any[]>([]),
    [selectedDay, setSelectedDay] = useState<any>(null);
  const reload = async () => {
    setRows(await api<any[]>("/progress"));
  };
  useEffect(() => {
    void reload().catch(onError);
    void api<any[]>("/progress/days").then(setDays).catch(onError);
  }, []);
  const priorities = rows.filter(
    (r) =>
      r.forgotten ||
      r.intent === "Learning" ||
      (r.attempts > 0 &&
        r.last_practised &&
        Date.now() - Date.parse(r.last_practised) > 14 * 86400000),
  );
  return (
    <>
      <div className="section-heading">
        <h2>Recent practice days</h2>
        <p>Recorded session time by day; this includes pauses.</p>
      </div>
      <div className="day-heatmap">
        {days.map((d) => (
          <TouchButton
            key={d.day}
            onClick={() => setSelectedDay(d)}
            style={{
              background: `rgba(80,120,60,${Math.min(0.8, 0.15 + d.recorded_seconds / 7200)})`,
            }}
          >
            {d.day.slice(5)}
            <small>{Math.round(d.recorded_seconds / 60)} min</small>
          </TouchButton>
        ))}
      </div>
      {selectedDay && (
        <p>
          {selectedDay.day} · {selectedDay.sessions} sessions ·{" "}
          {clock(selectedDay.recorded_seconds)} recorded
        </p>
      )}
      <div className="section-heading">
        <h2>Repertoire history</h2>
        <p>
          Time is attributed only to matched or manually labelled activities.
          Your personal learning levels are separate from machine measurements.
        </p>
      </div>
      <div className="progress-table">
        {rows.map((r) => (
          <div className="progress-row" key={r.id}>
            <div>
              <strong>
                {r.title} · {r.opus}
              </strong>
              <p>
                {r.intent}
                {r.mastery != null ? ` · self-assessed ${r.mastery}/3` : ""}
                {r.forgotten ? " · X — largely forgotten" : ""}
              </p>
              {r.machine?.latest_performance && (
                <p>
                  Latest performance:{" "}
                  {r.machine.latest_performance.performed.slice(0, 10)} ·{" "}
                  {r.machine.latest_performance.assessment
                    ? `${r.machine.latest_performance.assessment.precision_score}% pitch score`
                    : "No reliable score alignment"}
                  {r.machine.latest_performance.assessment?.audio_candidate
                    ? " · ★ Audio production candidate"
                    : ""}
                </p>
              )}
              {r.machine?.automatic_level && (
                <p>
                  Automatic piece level:{" "}
                  {r.machine.automatic_level.assessment.piece_level} (technical
                  proxy)
                </p>
              )}
              {r.machine?.revision_suggestion && (
                <p>{r.machine.revision_suggestion}</p>
              )}
              {r.machine?.personal_notes && (
                <p>Your notes: {r.machine.personal_notes}</p>
              )}
            </div>
            <span>
              {clock(r.seconds || 0)}
              <small>
                {r.attempts} activities · {r.complete || 0} complete
              </small>
            </span>
          </div>
        ))}
      </div>
      {rows
        .filter(
          (r) =>
            r.attempts ||
            r.seconds ||
            r.practice?.objectives?.length ||
            r.practice?.retention?.length,
        )
        .map((r) => (
          <PracticeProgress
            key={r.id}
            piece={r}
            reload={reload}
            onError={onError}
          />
        ))}
      <details>
        <summary>Add an objective for another piece</summary>
        {rows
          .filter(
            (r) =>
              !r.attempts &&
              !r.seconds &&
              !r.practice?.objectives?.length &&
              !r.practice?.retention?.length,
          )
          .map((r) => (
            <PracticeProgress
              key={r.id}
              piece={r}
              reload={reload}
              onError={onError}
            />
          ))}
      </details>
      <div className="section-heading">
        <h2>Ideas for your next session</h2>
        <p>
          Based on your stated goals and review flags; these are suggestions,
          not judgements of musical quality.
        </p>
      </div>
      <ul>
        {priorities.slice(0, 8).map((r) => (
          <li key={r.id}>
            {r.forgotten
              ? "Revisit from memory, then check the score: "
              : r.intent === "Learning"
                ? "Continue learning in manageable passages: "
                : "Review after time away: "}
            {r.title} · {r.opus}
          </li>
        ))}
      </ul>
    </>
  );
}
