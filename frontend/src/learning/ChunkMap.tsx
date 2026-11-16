import { RotateCcw } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { TouchButton as Button } from "../TouchButton";
import { range } from "./format";
import { RoutineEditor } from "./RoutineEditor";
import type { Config, NoteError, Snapshot, Target } from "./types";

type Props = {
  busy: boolean;
  data: Snapshot;
  setConfig: Dispatch<SetStateAction<Config | null>>;
  setChunkText: Dispatch<SetStateAction<string>>;
  setEditing: Dispatch<SetStateAction<boolean>>;
  editing: boolean;
  target: Target | null;
  reviewEnd: number | null;
  rule: NoteError | null;
  run: (
    path: string,
    body?: unknown,
    method?: string,
  ) => Promise<boolean | undefined>;
  includeCurrent: boolean;
  setIncludeCurrent: Dispatch<SetStateAction<boolean>>;
  config: Config | null;
  chunkText: string;
  onError: (error: unknown) => void;
};

export function ChunkMap({
  busy,
  data,
  setConfig,
  setChunkText,
  setEditing,
  editing,
  target,
  reviewEnd,
  rule,
  run,
  includeCurrent,
  setIncludeCurrent,
  config,
  chunkText,
  onError,
}: Props) {
  return (
    <div className="learning-card">
      <div className="section-heading">
        <h2>Your chunk map</h2>
        <Button
          disabled={busy || !!data.active || !!data.pending_at}
          onClick={() => {
            setConfig({ ...data.profile.config });
            setChunkText(
              data.profile.chunks.map((c) => `${c.start}-${c.end}`).join(", "),
            );
            setEditing(!editing);
          }}
        >
          Edit routine & chunks
        </Button>
      </div>
      {data.lesson.section_order && (
        <details open className="learning-progression">
          <summary>Proposed section progression</summary>
          <p>{data.lesson.plan_summary}</p>
          <ol>
            {data.lesson.section_order.map((index) => {
              const section = data.lesson.sections[index];
              return (
                <li key={index}>
                  <strong>
                    {section.title} · {range(section.start, section.end)}
                  </strong>
                </li>
              );
            })}
          </ol>
          <p>
            Then practise the transitions and assemble the larger blocks. Use
            each hand separately before coordinating; practise short, relaxed
            gestures before longer runs.
          </p>
        </details>
      )}
      <div className="learning-chunks">
        <Button
          className={`learning-chunk learning-chunk-review ${data.review.active && target?.start === data.review.learned_start && target?.end === reviewEnd ? "current" : ""}`}
          disabled={
            busy ||
            editing ||
            !!rule ||
            !data.ready ||
            !!data.active ||
            reviewEnd === null
          }
          title="Recall the learned span. Your learning position and streak are kept."
          onClick={() =>
            void run("/review", { include_current: includeCurrent })
          }
        >
          <RotateCcw size={16} />
          <span>
            {includeCurrent
              ? "Review through current chunk"
              : data.lesson.section_order
                ? "Review learned in this section"
                : "Review all learned"}
            <small>
              {reviewEnd === null
                ? "No learned chunks yet"
                : range(
                    includeCurrent
                      ? data.review.current_start
                      : (data.review.learned_start ??
                          data.review.current_start),
                    reviewEnd,
                  )}
            </small>
          </span>
        </Button>
        {data.profile.chunks.map((c, i) => {
          const resumeLearning =
            data.review.active && data.learning_target?.chunk === i;
          const done = data.profile.completed.some((id) =>
            id.includes(`:hidden:${c.start}:${c.end}`),
          );
          const className = `learning-chunk ${done ? "done" : ""} ${target?.chunk === i ? "current" : ""}`;
          return done || resumeLearning ? (
            <Button
              key={i}
              className={className}
              aria-label={
                resumeLearning
                  ? `Return to learning chunk ${range(c.start, c.end)}`
                  : `Review learned chunk ${range(c.start, c.end)}`
              }
              disabled={busy || editing || !!rule}
              title={
                resumeLearning
                  ? "Return to your current learning assignment."
                  : `Review this chunk. Your current learning position and streak are kept. ${c.focus}`
              }
              onClick={() =>
                void (resumeLearning
                  ? run("/review/leave")
                  : run("/review", { chunk_index: i }))
              }
            >
              {resumeLearning ? "↩ " : "✓ "}
              {range(c.start, c.end)}
            </Button>
          ) : (
            <span key={i} className={className} title={c.focus}>
              {range(c.start, c.end)}
            </span>
          );
        })}
      </div>
      <div className="learning-review">
        <h3>Previously learned chunks</h3>
        {data.review.active ? (
          <>
            <p>
              Reviewing measures {target && range(target.start, target.end)}.
              Your learning position and streak are kept.
            </p>
          </>
        ) : (
          <>
            <p>
              {data.review.learned_end !== null
                ? `Learned so far: ${range(data.review.learned_start ?? data.review.current_start, data.review.learned_end)}.`
                : "No completed hidden-recall chunks yet."}
            </p>
            <label className="learning-checkbox">
              <input
                type="checkbox"
                checked={includeCurrent}
                onChange={(event) => setIncludeCurrent(event.target.checked)}
              />
              Include the current chunk
            </label>
          </>
        )}
        <details>
          <summary>Future review plans</summary>
          <p>
            Learning restores this piece and hand’s saved position after
            restarting Studio. It offers learned passage review when available.
            Press Start review when ready, or Return to learning to continue
            your assignment. Spaced review scheduling is planned.
          </p>
        </details>
      </div>
      {editing && config && (
        <RoutineEditor
          chunkText={chunkText}
          data={data}
          run={run}
          setEditing={setEditing}
          onError={onError}
          config={config}
          setConfig={setConfig}
          setChunkText={setChunkText}
          busy={busy}
        />
      )}
    </div>
  );
}
