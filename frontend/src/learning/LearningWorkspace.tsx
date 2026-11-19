import { BookOpen, EyeOff, GraduationCap } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, json } from "../api";
import { LearningStaves } from "../LearningStaves";
import { Score } from "../Score";
import { TouchButton as Button } from "../TouchButton";
import { AttemptReview } from "./AttemptReview";
import { ChunkMap } from "./ChunkMap";
import { LearningControls } from "./LearningControls";
import { NoteRuleEditor } from "./NoteRuleEditor";
import { useReviewMistakeSound } from "./useReviewMistakeSound";

import { kindName, noteName, range } from "./format";
import {
  DEFAULT_SCORE_SHARE,
  SCORE_SHARE_KEY,
  clampScoreShare,
  savedScoreShare,
} from "./layout";
import type {
  Config,
  LearningProps,
  LessonChoice,
  NoteError,
  Snapshot,
} from "./types";

export function LearningWorkspace({
  pieces,
  volumes,
  settings,
  onError,
  onLibrary,
  onCertification,
  pieceId,
  choices,
  switching,
  onSelect,
}: LearningProps & {
  pieceId: string;
  choices: LessonChoice[];
  switching: boolean;
  onSelect: (pieceId: string) => Promise<void>;
}) {
  const endpoint = `/learning/${pieceId}`;
  const workspace = useRef<HTMLDivElement>(null);
  const [preferredShare, setPreferredShare] = useState(savedScoreShare);
  const [workspaceWidth, setWorkspaceWidth] = useState(0);
  const dragPointer = useRef<number | null>(null);
  const [scoreControlsHost, setScoreControlsHost] =
    useState<HTMLDivElement | null>(null);
  const [data, setData] = useState<Snapshot | null>(null);
  useReviewMistakeSound(data);
  const [busy, setBusy] = useState(false);
  const [peek, setPeek] = useState(false);
  const [peekTurns, setPeekTurns] = useState(
    () => localStorage.getItem("chopin-learning-peek-turns") !== "false",
  );
  const [peekPage, setPeekPage] = useState<{
    attempt: string;
    page: number;
    id: number;
  } | null>(null);
  const previousAttempt = useRef<string | null>(null);
  const [includeCurrent, setIncludeCurrent] = useState(false);
  const [editing, setEditing] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [chunkText, setChunkText] = useState("");
  const [rule, setRule] = useState<NoteError | null>(null);
  const [action, setAction] = useState("omit");
  const [fixReference, setFixReference] = useState(false);
  const [replacement, setReplacement] = useState("");
  const [reason, setReason] = useState("");
  const [dictatingReason, setDictatingReason] = useState(false);
  const [restart, setRestart] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [pedalRepeatEnabled, setPedalRepeatEnabled] = useState(true);
  const [pedalStatus, setPedalStatus] = useState("");
  const pedalState = useRef({ data, busy, editing, rule, run });
  pedalState.current = { data, busy, editing, rule, run };
  const scoreShare = clampScoreShare(preferredShare, workspaceWidth);
  const setScoreShare = (value: number) => {
    const next = clampScoreShare(value, workspaceWidth);
    setPreferredShare(next);
    try {
      localStorage.setItem(SCORE_SHARE_KEY, String(next));
    } catch {
      /* Layout still works without browser storage. */
    }
  };
  const dragDivider = (clientX: number) => {
    const box = workspace.current?.getBoundingClientRect();
    if (box) setScoreShare((clientX - box.left - 6) / (box.width - 12));
  };
  useEffect(() => {
    const element = workspace.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setWorkspaceWidth(entry.contentRect.width),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [!!data]);
  const piece = pieces.find((p) => p.id === pieceId);
  const volume = volumes.find((v) => v.id === piece?.volume_id);
  useEffect(() => {
    let live = true;
    const poll = () =>
      api<Snapshot>(endpoint)
        .then((value) => {
          if (live) setData(value);
        })
        .catch((error) => {
          if (live) onError(error);
        });
    void poll();
    const timer = setInterval(() => {
      setNow(Date.now());
      void poll();
    }, 900);
    const visibility = () => {
      if (document.hidden)
        void api(endpoint + "/pause", { method: "POST" }).catch(onError);
    };
    document.addEventListener("visibilitychange", visibility);
    return () => {
      live = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", visibility);
      void api(endpoint + "/pause", { method: "POST" }).catch(() => {});
    };
  }, []);
  useEffect(() => {
    setPeek(data?.active?.assisted ?? false);
    setRule(null);
  }, [data?.target?.id, data?.profile.hand, data?.profile.generation]);
  useEffect(() => {
    const attempt = data?.active?.id ?? null;
    // Replacing an active take (button, pedal or automatic retry) keeps the
    // score open. Finishing/pausing and starting afresh still resets the peek.
    if (!attempt || !previousAttempt.current) setPeek(false);
    previousAttempt.current = attempt;
    setRule(null);
  }, [data?.active?.id]);
  async function run(path: string, body?: unknown, method = "POST") {
    if (busy) return;
    setBusy(true);
    try {
      setData(
        await api<Snapshot>(
          endpoint + path,
          body === undefined ? { method } : json(method, body),
        ),
      );
      return true;
    } catch (error) {
      onError(error);
      return false;
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (!pedalRepeatEnabled) return;
    const owner = crypto.randomUUID();
    let live = true;
    let acquired = false;
    let after = 0;
    let timer: ReturnType<typeof setTimeout>;
    const release = () =>
      api(
        endpoint + "/pedal-control",
        json("POST", { owner, enabled: false }),
      ).catch(() => {});
    const poll = async () => {
      let delay = 180;
      try {
        if (document.hidden) {
          if (acquired) await release();
          acquired = false;
          return;
        }
        if (!acquired) {
          const cursor = await api<{ after: number }>(
            endpoint + "/pedal-control",
            json("POST", { owner, enabled: true }),
          );
          if (!live) {
            await release();
            return;
          }
          after = cursor.after;
          acquired = true;
        }
        const response = await api<{
          enabled: boolean;
          commands: { id: number }[];
        }>(
          endpoint +
            `/pedal-commands?owner=${encodeURIComponent(owner)}&after=${after}`,
        );
        if (!live) return;
        if (!response.enabled) {
          acquired = false;
          return;
        }
        setPedalStatus("");
        const command = response.commands.at(-1);
        if (!command) return;
        after = command.id;
        const current = pedalState.current;
        if (
          current.busy ||
          current.editing ||
          current.rule ||
          !current.data?.ready ||
          !current.data.target
        )
          return;
        await current.run("/pedal-repeat", {
          owner,
          command_id: command.id,
          attempt_id: current.data.active?.id || null,
          target_id: current.data.target.id,
        });
      } catch {
        if (live)
          setPedalStatus(
            "Pedal control is reconnecting. On-screen controls remain available.",
          );
        acquired = false;
        delay = 1000;
      } finally {
        if (live) timer = setTimeout(poll, delay);
      }
    };
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
      void release();
    };
  }, [pedalRepeatEnabled]);

  // Pin the full PDF to this lesson's reviewed edition and page range. Learning
  // never opens the provisional XML viewer or a different selected Practice piece.
  const learningPiece = useMemo(
    () =>
      piece && data
        ? {
            ...piece,
            start_page: data.lesson.source.pdf_pages[0],
            end_page: data.lesson.source.pdf_pages[1],
            view: JSON.stringify({
              page: data.target_page,
              zoom: 1,
              two_pages: false,
              crop: 0,
            }),
          }
        : null,
    [
      piece,
      data?.target_page,
      data?.lesson.source.pdf_pages[0],
      data?.lesson.source.pdf_pages[1],
    ],
  );
  if (!data || (!config && editing))
    return (
      <section className="content">
        <p>Loading Learning…</p>
      </section>
    );
  const target = data.active?.target || data.target;
  const reviewEnd = includeCurrent
    ? data.review.current_end
    : data.review.learned_end;
  const hidden = target?.kind !== "visible";
  const scoreVisible = !!target && (!hidden || peek);
  const result = !data.active ? data.history[0]?.result : null;
  const previousResult = data.history.find(
    (take) => take.id !== data.active?.id,
  )?.result;
  const required =
    target &&
    (["visible", "hidden"].includes(target.kind)
      ? data.profile.config[target.kind as "visible" | "hidden"]
      : data.profile.config.connections);
  const countDown = data.pending_at
    ? Math.max(0, Math.ceil(data.pending_at - now / 1000))
    : 0;
  return (
    <section className="content learning">
      <div className="page-heading learning-heading">
        <div>
          <h1>Learning</h1>
          <p>{data.lesson.title}</p>
        </div>
        <label className="learning-piece-choice">
          Learning piece
          <select
            aria-label="Learning piece"
            value={pieceId}
            disabled={switching || busy}
            onChange={(e) => void onSelect(e.target.value)}
          >
            {choices.map((choice) => (
              <option key={choice.piece_id} value={choice.piece_id}>
                {choice.title}
              </option>
            ))}
          </select>
        </label>
        <GraduationCap size={30} />
      </div>
      {data.profile.previous_profile && (
        <div className="banner" role="status">
          The reviewed digital edition starts fresh note checks. Your previous
          scan-study profile and attempts are retained as history; your routine
          and chosen hand are kept.
        </div>
      )}
      {!data.automatic_ready && (
        <div className="banner" role="status">
          Digital counterpart: provisional. Study the Paderewski scan, finish
          each take and use Count take as remembered or Next stage. Automatic
          grading, finish, mistake restart and staff comparison await full note
          review.
        </div>
      )}
      <div
        className="learning-workspace"
        ref={workspace}
        style={{
          gridTemplateColumns: `minmax(0, ${scoreShare}fr) 12px minmax(0, ${1 - scoreShare}fr)`,
        }}
      >
        <div className="learning-pdf">
          <Score
            learningMode
            fullscreenTarget={workspace}
            controlsHost={scoreControlsHost}
            requestedPage={data.target_page}
            onFullscreenHost={(host) => {
              if (host)
                host
                  .querySelector(".learning-control-panel")
                  ?.scrollTo({ top: 0 });
            }}
            concealed={!scoreVisible || !data.ready}
            concealedContent={
              !data.ready ? (
                <div className="learning-hidden">
                  <BookOpen size={38} />
                  <h2>Open the reviewed Paderewski score</h2>
                  <p>{data.source_notice}</p>
                  <Button onClick={onLibrary}>Open score library</Button>
                </div>
              ) : (
                <div className="learning-hidden" aria-label="Score hidden">
                  <EyeOff size={38} />
                  <h2>
                    {target
                      ? "Recall the passage without the score"
                      : "Lesson completed"}
                  </h2>
                  <p>
                    {target
                      ? `Measures ${range(target.start, target.end)} · take your time.`
                      : "Review the lesson or move to Practice."}
                  </p>
                </div>
              )
            }
            piece={learningPiece}
            volume={data.ready ? volume : undefined}
            settings={{ ...settings, live_auto_turn: false }}
            onLibrary={onLibrary}
            onClear={() => {}}
            onAutoTurnChange={async () => {}}
            command={null}
            automaticCommand={
              peek &&
              peekTurns &&
              data.active?.id === peekPage?.attempt &&
              peekPage
                ? {
                    action: "go",
                    piece_id: pieceId,
                    page: peekPage.page,
                    id: peekPage.id,
                  }
                : null
            }
            onError={onError}
            onToggle={() => {}}
          />
        </div>
        <div
          className="learning-divider"
          role="separator"
          aria-label="Resize score and controls"
          aria-orientation="vertical"
          aria-valuemin={Math.round(clampScoreShare(0, workspaceWidth) * 100)}
          aria-valuemax={Math.round(clampScoreShare(1, workspaceWidth) * 100)}
          aria-valuenow={Math.round(scoreShare * 100)}
          aria-valuetext={`Score ${Math.round(scoreShare * 100)} percent; controls ${Math.round((1 - scoreShare) * 100)} percent`}
          tabIndex={0}
          title="Drag to resize. Arrow keys adjust; double-click or Enter restores the default."
          onPointerDown={(event) => {
            if (event.button !== 0) return;
            event.preventDefault();
            event.currentTarget.focus();
            dragPointer.current = event.pointerId;
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (dragPointer.current === event.pointerId)
              dragDivider(event.clientX);
          }}
          onPointerUp={(event) => {
            if (dragPointer.current !== event.pointerId) return;
            dragDivider(event.clientX);
            dragPointer.current = null;
            event.currentTarget.releasePointerCapture(event.pointerId);
          }}
          onPointerCancel={() => {
            dragPointer.current = null;
          }}
          onLostPointerCapture={() => {
            dragPointer.current = null;
          }}
          onDoubleClick={() => setScoreShare(DEFAULT_SCORE_SHARE)}
          onKeyDown={(event) => {
            const step = event.shiftKey ? 0.05 : 0.02;
            const next =
              event.key === "ArrowLeft"
                ? scoreShare - step
                : event.key === "ArrowRight"
                  ? scoreShare + step
                  : event.key === "Home"
                    ? 0
                    : event.key === "End"
                      ? 1
                      : event.key === "Enter"
                        ? DEFAULT_SCORE_SHARE
                        : null;
            if (next !== null) {
              event.preventDefault();
              setScoreShare(next);
            }
          }}
        />
        <aside
          className="learning-control-panel"
          aria-label="Learning controls"
        >
          <div
            className={`banner learning-source-status ${data.ready ? "" : "error"}`}
            role="status"
          >
            {data.source_notice}. {data.lesson.corrections.length} documented
            corrections to the first-edition conversion.
          </div>
          {data.controller_error && (
            <div className="banner error" role="alert">
              {data.controller_error}
            </div>
          )}
          <div className="learning-summary">
            <span>
              {data.progress.completed} / {data.progress.total} stages completed
            </span>
            <progress
              max={data.progress.total}
              value={data.progress.completed}
            />
            <span>Personal note rules: {data.profile.variants.length}</span>
          </div>
          <LearningControls
            data={data}
            busy={busy}
            editing={editing}
            rule={rule}
            run={run}
            target={target}
            required={required}
            hidden={hidden}
            peek={peek}
            setPeek={setPeek}
            countDown={countDown}
            pedalRepeatEnabled={pedalRepeatEnabled}
            setPedalRepeatEnabled={setPedalRepeatEnabled}
            pedalStatus={pedalStatus}
            previousResult={previousResult}
          />
          <label className="learning-checkbox">
            <input
              type="checkbox"
              checked={peekTurns}
              onChange={(event) => {
                setPeekTurns(event.target.checked);
                localStorage.setItem(
                  "chopin-learning-peek-turns",
                  String(event.target.checked),
                );
              }}
            />
            Turn score pages automatically while peeking
          </label>
          {data.active?.assisted && hidden && (
            <div className="banner">
              {target?.review_mode === "expanding"
                ? "Score peek recorded. Finish the take, then use Mark review take correct to expand the review by your own judgement."
                : "Assisted attempt: consulting the score means this recall will not count toward advancement."}
            </div>
          )}
          <div className="learning-score-controls" ref={setScoreControlsHost} />
          {data.active && data.automatic_ready && (
            <div
              className="learning-card learning-result"
              role="region"
              aria-label="Review this attempt"
            >
              <LearningStaves
                pieceId={pieceId}
                key={data.active.id}
                attemptId={data.active.id}
                active
                revealExpected={scoreVisible}
                onFollowPage={(page) =>
                  setPeekPage((previous) =>
                    page === null
                      ? null
                      : previous?.attempt === data.active!.id &&
                          previous.page === page
                        ? previous
                        : { attempt: data.active!.id, page, id: Date.now() },
                  )
                }
              />
            </div>
          )}
          {result && (
            <AttemptReview
              result={result}
              data={data}
              busy={busy}
              run={run}
              pieceId={pieceId}
              scoreVisible={scoreVisible}
              setRule={setRule}
              setFixReference={setFixReference}
              setReason={setReason}
              setReplacement={setReplacement}
              setAction={setAction}
            />
          )}
          {rule && (
            <NoteRuleEditor
              dictatingReason={dictatingReason}
              rule={rule}
              action={action}
              replacement={replacement}
              onError={onError}
              run={run}
              fixReference={fixReference}
              setRule={setRule}
              setAction={setAction}
              setReplacement={setReplacement}
              busy={busy}
              reason={reason}
              setReason={setReason}
              setDictatingReason={setDictatingReason}
            />
          )}
          <details className="learning-card">
            <summary>
              Reference note corrections (
              {data.profile.corrections?.length || 0})
            </summary>
            <p>
              Corrections to individual notes in this local Learning reference,
              separate from personal playing adaptations. Old takes retain their
              original reference.
            </p>
            {(data.profile.corrections || []).map((correction) => (
              <div className="learning-rule" key={correction.note_id}>
                <span>
                  Measure {correction.measure}:{" "}
                  {noteName(correction.original_pitch)} →{" "}
                  {correction.spelling
                    ? `${correction.spelling.step}${correction.spelling.alter === -1 ? "♭" : correction.spelling.alter === 1 ? "♯" : "♮"}${correction.spelling.octave}`
                    : noteName(correction.pitch)}
                  . {correction.reason}
                </span>
                <Button
                  disabled={busy || !!data.active}
                  onClick={() =>
                    void run("/corrections", {
                      note_id: correction.note_id,
                      action: "revoke",
                      reason: "Undo reference correction",
                    })
                  }
                >
                  Undo correction
                </Button>
              </div>
            ))}
          </details>
          <details className="learning-card">
            <summary>
              Personal note rules ({data.profile.variants.length})
            </summary>
            <p>
              These rules apply to this edition revision and carry through
              cumulative passages. Old attempts retain the rules used at the
              time.
            </p>
            {data.profile.variants.map((v) => (
              <div className="learning-rule" key={v.note_id}>
                <span>
                  Measure {v.measure}: {noteName(v.original_pitch)} →{" "}
                  {v.action === "omit" ? "omitted" : noteName(v.pitch)}.{" "}
                  {v.reason}
                </span>
                <Button
                  disabled={busy || !!data.active}
                  onClick={() =>
                    void run("/variants", {
                      ...v,
                      action: "revoke",
                      reason: "Restore the printed note",
                    })
                  }
                >
                  Revoke rule
                </Button>
              </div>
            ))}
          </details>
          <ChunkMap
            busy={busy}
            data={data}
            setConfig={setConfig}
            setChunkText={setChunkText}
            setEditing={setEditing}
            editing={editing}
            target={target}
            reviewEnd={reviewEnd}
            rule={rule}
            run={run}
            includeCurrent={includeCurrent}
            setIncludeCurrent={setIncludeCurrent}
            config={config}
            chunkText={chunkText}
            onError={onError}
          />
          <details className="learning-card">
            <summary>Lesson analysis & edition evidence</summary>
            <p>
              {data.lesson.reviewer}. {data.lesson.scope}
            </p>
            <p>
              {data.lesson.plan_summary ||
                "The plan uses short opening patterns, single measures through the changing middle, then return and coda groups. Similar passages are learned as separate occurrences."}
            </p>
            <p>
              Each chunk receives visible study and hidden recall, then section
              connections.
              {data.lesson.section_order
                ? " Independent sections follow the order below; transition drills and larger assemblies join the form afterward. The coda is acquired backwards from its ending."
                : " Completed sections are cumulatively connected from the pickup."}
            </p>
            <p>
              Every new proper Learning piece requires an in-depth model
              analysis and edition review. Automatic chunk proposals, if added,
              must remain flagged provisional.
            </p>
            {data.lesson.review_gaps && (
              <ul>
                {data.lesson.review_gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            )}
            <a href={`/api/learning/${pieceId}/reference`} download>
              {data.automatic_ready
                ? "Download the reviewed digital counterpart and correction log"
                : "Download the provisional digital draft and review gaps"}
            </a>
            <p>
              <a
                href={`/api/learning/${pieceId}/reference?format=musicxml`}
                download
              >
                {data.automatic_ready
                  ? "Download the unmeasured pitch/attack study (MusicXML)"
                  : "Download the provisional unmeasured draft (MusicXML)"}
              </a>
            </p>
          </details>
          {data.automatic_ready && (
            <details className="learning-card">
              <summary>Score tools</summary>
              <Button
                className="secondary"
                disabled={busy || !!data.active}
                onClick={() => onCertification(pieceId)}
              >
                Score certification
              </Button>
            </details>
          )}
          <details className="learning-card">
            <summary>Recent attempts</summary>
            {data.history.map((h) => (
              <p key={h.id}>
                Measures {range(h.target.start, h.target.end)} ·{" "}
                {kindName(h.target.kind)} ·{" "}
                {h.result?.manual_accepted
                  ? "self-assessed remembered"
                  : h.result?.passed
                    ? "correct"
                    : h.result?.auto_restarted
                      ? "automatically restarted (streak kept)"
                      : h.result?.restarted
                        ? "restarted (streak kept)"
                        : h.result?.aborted
                          ? "paused"
                          : h.status === "interrupted"
                            ? "interrupted"
                            : h.result
                              ? data.automatic_ready
                                ? "needs another attempt"
                                : "ungraded · awaiting self-assessment"
                              : "recording"}{" "}
                ·{" "}
                {h.session_id ? (
                  <a href={`/api/sessions/${h.session_id}/midi`}>MIDI</a>
                ) : (
                  "MIDI deleted"
                )}
              </p>
            ))}
          </details>
          <div className="learning-controls">
            <Button
              disabled={busy || !!data.active}
              onClick={() => setRestart(!restart)}
            >
              Restart this piece’s progression
            </Button>
            {restart && (
              <>
                <span>
                  Progress resets; recordings and personal note rules stay
                  saved.
                </span>
                <Button
                  disabled={busy}
                  onClick={async () => {
                    await run("/restart");
                    setRestart(false);
                  }}
                >
                  Confirm restart
                </Button>
              </>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
