import { Check, Eye, EyeOff, Pause, Play, RotateCcw } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { TouchButton as Button } from "../TouchButton";
import { kindName, range } from "./format";
import type { NoteError, Result, Snapshot, Target } from "./types";

type Props = {
  data: Snapshot;
  busy: boolean;
  editing: boolean;
  rule: NoteError | null;
  run: (
    path: string,
    body?: unknown,
    method?: string,
  ) => Promise<boolean | undefined>;
  target: Target | null;
  required: number | null;
  hidden: boolean;
  peek: boolean;
  setPeek: Dispatch<SetStateAction<boolean>>;
  countDown: number;
  pedalRepeatEnabled: boolean;
  setPedalRepeatEnabled: Dispatch<SetStateAction<boolean>>;
  pedalStatus: string;
  previousResult: Result | null | undefined;
};

export function LearningControls({
  data,
  busy,
  editing,
  rule,
  run,
  target,
  required,
  hidden,
  peek,
  setPeek,
  countDown,
  pedalRepeatEnabled,
  setPedalRepeatEnabled,
  pedalStatus,
  previousResult,
}: Props) {
  return (
    <div className="learning-target">
      <div>
        <label className="learning-hand-control">
          Hands
          <select
            aria-label="Practice hands"
            title="Progress is saved separately for each hand. Finish or pause the current attempt before switching."
            value={data.profile.hand || "both"}
            disabled={busy || !!data.active || editing || !!rule}
            onChange={(event) =>
              void run("/hand", { hand: event.target.value }, "PUT")
            }
          >
            <option value="both">Both hands</option>
            <option value="right">Right hand</option>
            <option value="left">Left hand</option>
          </select>
        </label>
        {!data.automatic_ready && (
          <p className="learning-reference-badge">
            Scan study · self-assessed progress · digital notes provisional
          </p>
        )}
        <span className="eyebrow">{kindName(target?.kind)}</span>
        <p className="learning-location">
          Current chunk starts on PDF page {data.target_page}
        </p>
        <h2>
          {target
            ? `Measures ${range(target.start, target.end)}`
            : "All note-recall stages complete"}
        </h2>

        <p className="muted">
          {data.review.active
            ? "Review only: no repetition quota or stage advancement."
            : target
              ? `${data.profile.streak} / ${required} consecutive ${data.automatic_ready ? "correct" : "self-assessed remembered"} attempts in this stage.`
              : ""}{" "}
          No tempo, duration, dynamics or pedal grade.
        </p>
      </div>
      {target?.review_mode === "expanding" && (
        <p role="status">
          {target.review_complete
            ? "Expanding review complete · all learned chunks recalled."
            : `Build backward · last ${target.chunk_count} of ${target.total_chunks} learned chunks. An unassisted pass adds two earlier chunks. Press Start review for the next length.`}
        </p>
      )}
      <div className="learning-controls">
        {data.active ? (
          <>
            <span className="learning-recording">
              <span className="record-dot" /> MIDI recording
            </span>
            <Button
              className="primary"
              disabled={busy}
              onClick={() => void run("/finish")}
            >
              <Check size={18} />
              Finish & evaluate
            </Button>
            <Button
              disabled={busy}
              title="Restart immediately and keep your correct-attempt streak"
              onClick={() =>
                void run("/restart-take", { attempt_id: data.active!.id })
              }
            >
              <RotateCcw size={18} /> Restart take
            </Button>
          </>
        ) : (
          target && (
            <Button
              className="primary"
              disabled={
                busy || !data.ready || !!data.pending_at || editing || !!rule
              }
              onClick={() => void run("/start")}
            >
              <Play size={18} />
              {data.review.active ? "Start review" : "Start attempt"}
            </Button>
          )
        )}
        {data.review.active && (
          <Button disabled={busy} onClick={() => void run("/review/leave")}>
            Return to learning
          </Button>
        )}
        {(data.active || data.pending_at) && (
          <Button disabled={busy} onClick={() => void run("/pause")}>
            <Pause size={18} />
            Pause learning
          </Button>
        )}
        {target && !data.review.active && (
          <Button
            disabled={busy || !data.ready || editing || !!rule}
            title="Advance by your own memory assessment without completing the remaining repetitions"
            onClick={() =>
              void run("/advance", {
                stage_id: target.id,
                generation: data.profile.generation,
              })
            }
          >
            Next stage
          </Button>
        )}
        {hidden && target && (
          <Button
            disabled={busy}
            onClick={async () => {
              if (!peek) {
                if (await run("/peek")) setPeek(true);
              } else setPeek(false);
            }}
          >
            {peek ? <EyeOff size={18} /> : <Eye size={18} />}
            {peek ? "Hide score" : "Peek at score"}
          </Button>
        )}
      </div>
      {data.pending_at && (
        <p role="status">
          Next attempt starts in {countDown}s. Pause to take a break or review
          an error.
        </p>
      )}
      <label className="learning-checkbox learning-pedal-control">
        <input
          type="checkbox"
          checked={pedalRepeatEnabled}
          onChange={(event) => setPedalRepeatEnabled(event.target.checked)}
        />
        Middle pedal: repeat attempt
      </label>
      {pedalStatus && <p role="status">{pedalStatus}</p>}
      {data.profile.config.auto_restart_on_mistake && (
        <p className="muted">
          Auto-restart on mistakes is on. Release all keys to restart.
        </p>
      )}
      {data.active && previousResult?.auto_restarted && (
        <p role="status">
          Take automatically restarted. Previous MIDI saved; your streak is
          unchanged.
        </p>
      )}
      <details className="learning-guidance">
        <summary>Passage guidance & attempt help</summary>
        <p>
          {target?.focus ||
            "Your note-learning history is saved. Performance work remains available in Practice."}
        </p>
        <p>
          Auto finish waits for a complete correct passage, released keys and a
          short settling interval. For a mistaken or unfinished attempt, use
          Finish & evaluate, or enable auto-restart on mistakes in Edit routine
          & chunks. Long thinking pauses are allowed. In Learning, press and
          release the middle pedal (CC66) to restart the current take, or start
          a new one when idle. It does not turn pages and does not change the
          piano’s sostenuto function.
        </p>
      </details>
    </div>
  );
}
