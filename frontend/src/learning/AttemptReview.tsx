import { Check } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { LearningStaves } from "../LearningStaves";
import { TouchButton as Button } from "../TouchButton";
import type { NoteError, Result, Snapshot } from "./types";

type Props = {
  result: Result;
  data: Snapshot;
  busy: boolean;
  run: (
    path: string,
    body?: unknown,
    method?: string,
  ) => Promise<boolean | undefined>;
  pieceId: string;
  scoreVisible: boolean;
  setRule: Dispatch<SetStateAction<NoteError | null>>;
  setFixReference: Dispatch<SetStateAction<boolean>>;
  setReason: Dispatch<SetStateAction<string>>;
  setReplacement: Dispatch<SetStateAction<string>>;
  setAction: Dispatch<SetStateAction<string>>;
};

export function AttemptReview({
  result,
  data,
  busy,
  run,
  pieceId,
  scoreVisible,
  setRule,
  setFixReference,
  setReason,
  setReplacement,
  setAction,
}: Props) {
  return (
    <div
      className={`learning-card learning-result ${result.passed ? "passed" : ""}`}
      role="status"
    >
      <h2>
        {result.manual_accepted
          ? "Counted as remembered"
          : result.passed
            ? "Correct recall"
            : result.aborted
              ? "Paused and saved"
              : result.assisted
                ? "Assisted recall"
                : "Review this attempt"}
      </h2>
      <p>
        {result.manual_accepted
          ? data.automatic_ready
            ? "Your memory judgement counted this take toward the streak. The original pitch differences remain below."
            : "Your memory judgement counted this take toward the streak. The provisional digital reference supplied no automatic pitch verdict."
          : result.notice}
      </p>
      {!result.passed &&
        !result.manual_accepted &&
        !result.aborted &&
        !result.assisted &&
        result.capture_ok &&
        data.history[0].target.kind !== "review" && (
          <Button
            className="primary"
            disabled={busy || !!data.active}
            onClick={() => void run(`/attempts/${data.history[0].id}/accept`)}
          >
            <Check size={18} /> Count take as remembered
          </Button>
        )}
      {data.history[0].session_id && data.automatic_ready && (
        <LearningStaves
          pieceId={pieceId}
          key={data.history[0].id}
          attemptId={data.history[0].id}
          active={false}
          revealExpected={!data.pending_at || scoreVisible}
        />
      )}
      {result.errors.length > 0 && (
        <ul>
          {result.errors.slice(0, 24).map((error, i) => (
            <li key={i}>
              <span>
                {error.kind === "missing"
                  ? `Missing ${error.name} · measure ${error.measure} · ${error.staff === 1 ? "upper" : "lower"} staff`
                  : `Extra ${error.name}`}
              </span>
              {error.id && (
                <>
                  <Button
                    disabled={busy}
                    onClick={async () => {
                      if (data.pending_at && !(await run("/pause"))) return;
                      setRule(error);
                      setFixReference(true);
                      setReason(
                        "Incorrect transcription of the printed score.",
                      );
                      setReplacement(error.name);
                      setAction("replace");
                    }}
                  >
                    Fix reference note
                  </Button>
                  <Button
                    disabled={busy}
                    onClick={async () => {
                      if (data.pending_at && !(await run("/pause"))) return;
                      setRule(error);
                      setFixReference(false);
                      setReason("");
                      setReplacement(error.name);
                      setAction("omit");
                    }}
                  >
                    Overrule error
                  </Button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      {result.error_count > 24 && (
        <p>
          {result.error_count - 24} further differences. Work on a smaller chunk
          to review them individually.
        </p>
      )}
      {data.history[0].session_id && data.automatic_ready && (
        <a href={`/api/sessions/${data.history[0].session_id}/midi`}>
          Download this attempt’s MIDI
        </a>
      )}
    </div>
  );
}
