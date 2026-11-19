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
  const expandingReview = data.history[0].target.review_mode === "expanding";
  const original = data.history[0].target.review_full_target;
  const currentReview = data.target?.review_full_target || data.target;
  const completedReviewSequence =
    original?.review_mode === "expanding" &&
    data.history[0].target.end === original.end &&
    data.target?.id === original.id;
  return (
    <div
      className={`learning-card learning-result ${result.passed ? "passed" : ""}`}
      role="status"
    >
      <h2>
        {result.review_sequence_accepted
          ? "Review sequence marked correct"
          : result.manual_accepted
            ? expandingReview
              ? "Review marked correct"
              : "Counted as remembered"
            : result.passed
              ? "Correct recall"
              : result.aborted
                ? "Paused and saved"
                : result.assisted
                  ? "Assisted recall"
                  : "Review this attempt"}
      </h2>
      <p>
        {result.review_sequence_accepted
          ? "Your judgement advanced the build-backward review. Each recorded part keeps its original pitch verdict; no uninterrupted full-range pass is claimed."
          : result.manual_accepted
            ? expandingReview
              ? "You marked this review correct. The next review length is ready, or the full review is complete. Score peeks and original pitch results remain recorded; learning progress is unchanged."
              : data.automatic_ready
                ? "Your memory judgement counted this take toward the streak. The original pitch differences remain below."
                : "Your memory judgement counted this take toward the streak. The provisional digital reference supplied no automatic pitch verdict."
            : result.notice}
      </p>
      {completedReviewSequence &&
        !result.review_sequence_accepted &&
        !result.aborted &&
        result.capture_ok && (
          <Button
            className="primary"
            disabled={busy || !!data.active}
            onClick={() => void run(`/attempts/${data.history[0].id}/accept`)}
          >
            Mark review sequence correct
          </Button>
        )}
      {data.review.active &&
        data.automatic_ready &&
        data.history[0].target.kind === "review" &&
        currentReview?.id === (original || data.history[0].target).id &&
        data.history[0].session_id &&
        result.capture_ok && (
          <Button
            disabled={busy || !!data.active}
            onClick={() =>
              void run("/restart-take", { attempt_id: data.history[0].id })
            }
          >
            Retake last measure
          </Button>
        )}
      {!result.passed &&
        !result.manual_accepted &&
        !result.aborted &&
        (!result.assisted || expandingReview) &&
        result.capture_ok &&
        (data.history[0].target.kind !== "review" ||
          (expandingReview &&
            data.review.active &&
            data.target?.id === data.history[0].target.id)) && (
          <Button
            className="primary"
            disabled={busy || !!data.active}
            onClick={() => void run(`/attempts/${data.history[0].id}/accept`)}
          >
            <Check size={18} />{" "}
            {expandingReview
              ? "Mark review take correct"
              : "Count take as remembered"}
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
