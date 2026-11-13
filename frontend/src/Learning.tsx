import { ReasonDictation } from "./ReasonDictation";
import { LearningStaves } from "./LearningStaves";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Eye,
  EyeOff,
  Pause,
  Play,
  BookOpen,
  GraduationCap,
  Check,
  RotateCcw,
} from "lucide-react";
import { api, json, type Piece, type Settings, type Volume } from "./api";
import { Score } from "./Score";
import { TouchButton as Button } from "./TouchButton";

type Config = {
  visible: number;
  hidden: number;
  connections: number;
  auto_continue: boolean;
  auto_finish: boolean;
  auto_restart_on_mistake: boolean;
};
type Chunk = {
  start: number;
  end: number;
  section: number;
  label: string;
  focus: string;
};
type Target = {
  id: string;
  kind: string;
  start: number;
  end: number;
  chunk: number;
  focus: string;
};
type NoteError = {
  kind: string;
  id?: string;
  pitch: number;
  name: string;
  measure?: number;
  staff?: number;
};
type Result = {
  passed: boolean;
  manual_accepted?: boolean;
  capture_ok?: boolean;
  notice: string;
  errors: NoteError[];
  error_count: number;
  errors_truncated?: boolean;
  assisted?: boolean;
  aborted?: boolean;
  restarted?: boolean;
  auto_restarted?: boolean;
};
type Variant = {
  note_id: string;
  action: string;
  pitch: number;
  reason: string;
  measure: number;
  original_pitch: number;
  spelling?: { step: string; alter: number; octave: number } | null;
};
type Snapshot = {
  lesson: {
    title: string;
    analysis_status: string;
    revision: string;
    scope: string;
    reviewer: string;
    corrections: unknown[];
    sections: { start: number; end: number; title: string }[];
  };
  ready: boolean;
  source_notice: string;
  controller_error: string | null;
  target_page: number;
  profile: {
    config: Config;
    hand?: "both" | "right" | "left";
    chunks: Chunk[];
    variants: Variant[];
    corrections?: Variant[];
    stage_index: number;
    generation: number;
    streak: number;
    completed: string[];
  };
  target: Target | null;
  learning_target: Target | null;
  review: {
    active: boolean;
    learned_end: number | null;
    current_end: number | null;
  };
  active: {
    id: string;
    session_id: string;
    target: Target;
    assisted: boolean;
  } | null;
  pending_at: number | null;
  progress: { completed: number; total: number };
  history: {
    id: string;
    session_id: string | null;
    status: string;
    target: Target;
    result: Result | null;
  }[];
};
const SCORE_SHARE_KEY = "chopin-learning-score-share";
const DEFAULT_SCORE_SHARE = 2 / 3;
function clampScoreShare(value: number, width = 0) {
  const available = Math.max(1, width - 12);
  const minimum = width
    ? Math.max(0.35, Math.min(220, width * 0.4) / available)
    : 0.35;
  const maximum = width
    ? Math.min(0.8, 1 - Math.min(240, width * 0.4) / available)
    : 0.8;
  return Math.max(minimum, Math.min(maximum, value));
}
function savedScoreShare() {
  try {
    const saved = localStorage.getItem(SCORE_SHARE_KEY);
    const value = saved === null ? DEFAULT_SCORE_SHARE : Number(saved);
    return Number.isFinite(value)
      ? clampScoreShare(value)
      : DEFAULT_SCORE_SHARE;
  } catch {
    return DEFAULT_SCORE_SHARE;
  }
}
const endpoint = "/learning/e25-1";
const kindName = (kind?: string) =>
  ({
    visible: "Study with the score",
    hidden: "Recall from memory",
    connection: "Connect this section",
    cumulative: "Recall all learned sections",
    review: "Previously learned chunks · review",
  })[kind || "visible"];
const range = (a: number, b: number) =>
  `${a === 0 ? "Pickup" : a}${a === b ? "" : `–${b}`}`;
const noteName = (p: number) =>
  ["C", "D♭", "D♮", "E♭", "E♮", "F", "G♭", "G", "A♭", "A♮", "B♭", "B♮"][
    p % 12
  ] +
  (Math.floor(p / 12) - 1);
function noteNumber(name: string) {
  const match = /^([A-Ga-g])([#b♯♭♮]?)(-?\d)$/.exec(name.trim());
  if (!match) throw new Error("Enter a note such as C4, F#4 or B♭3.");
  const pitch =
    (Number(match[3]) + 1) * 12 +
    ({ C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[match[1].toUpperCase()] ||
      0) +
    (["#", "♯"].includes(match[2])
      ? 1
      : ["b", "♭"].includes(match[2])
        ? -1
        : 0);
  if (pitch < 0 || pitch > 127)
    throw new Error("That note is outside the MIDI range.");
  return pitch;
}

export function Learning({
  pieces,
  volumes,
  settings,
  onError,
  onLibrary,
}: {
  pieces: Piece[];
  volumes: Volume[];
  settings: Settings;
  onError: (error: unknown) => void;
  onLibrary: () => void;
}) {
  const workspace = useRef<HTMLDivElement>(null);
  const [preferredShare, setPreferredShare] = useState(savedScoreShare);
  const [workspaceWidth, setWorkspaceWidth] = useState(0);
  const dragPointer = useRef<number | null>(null);
  const [scoreControlsHost, setScoreControlsHost] =
    useState<HTMLDivElement | null>(null);
  const [data, setData] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [peek, setPeek] = useState(false);
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
  const piece = pieces.find((p) => p.id === "e25-1");
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
    setPeek(false);
    setRule(null);
  }, [data?.active?.id, data?.target?.id]);
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
            start_page: 64,
            end_page: 68,
            view: JSON.stringify({
              page: data.target_page,
              zoom: 1,
              two_pages: false,
              crop: 0,
            }),
          }
        : null,
    [piece, data?.target_page],
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
        <GraduationCap size={30} />
      </div>
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
            automaticCommand={null}
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
                    ? `${data.profile.streak} / ${required} consecutive correct attempts in this stage.`
                    : ""}{" "}
                No tempo, duration, dynamics or pedal grade.
              </p>
            </div>
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
                      busy ||
                      !data.ready ||
                      !!data.pending_at ||
                      editing ||
                      !!rule
                    }
                    onClick={() => void run("/start")}
                  >
                    <Play size={18} />
                    {data.review.active ? "Start review" : "Start attempt"}
                  </Button>
                )
              )}
              {data.review.active && (
                <Button
                  disabled={busy}
                  onClick={() => void run("/review/leave")}
                >
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
                Next attempt starts in {countDown}s. Pause to take a break or
                review an error.
              </p>
            )}
            <label className="learning-checkbox learning-pedal-control">
              <input
                type="checkbox"
                checked={pedalRepeatEnabled}
                onChange={(event) =>
                  setPedalRepeatEnabled(event.target.checked)
                }
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
                Take automatically restarted. Previous MIDI saved; your streak
                is unchanged.
              </p>
            )}
            <details className="learning-guidance">
              <summary>Passage guidance & attempt help</summary>
              <p>
                {target?.focus ||
                  "Your note-learning history is saved. Performance work remains available in Practice."}
              </p>
              <p>
                Auto finish waits for a complete correct passage, released keys
                and a short settling interval. For a mistaken or unfinished
                attempt, use Finish & evaluate, or enable auto-restart on
                mistakes in Edit routine & chunks. Long thinking pauses are
                allowed. In Learning, press and release the middle pedal (CC66)
                to restart the current take, or start a new one when idle. It
                does not turn pages and does not change the piano’s sostenuto
                function.
              </p>
            </details>
          </div>
          {data.active?.assisted && hidden && (
            <div className="banner">
              Assisted attempt: consulting the score means this recall will not
              count toward advancement.
            </div>
          )}
          <div className="learning-score-controls" ref={setScoreControlsHost} />
          {data.active && (
            <div
              className="learning-card learning-result"
              role="region"
              aria-label="Review this attempt"
            >
              <LearningStaves
                key={data.active.id}
                attemptId={data.active.id}
                active
                revealExpected={scoreVisible}
              />
            </div>
          )}
          {result && (
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
                  ? "Your memory judgement counted this take toward the streak. The original pitch differences remain below."
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
                    onClick={() =>
                      void run(`/attempts/${data.history[0].id}/accept`)
                    }
                  >
                    <Check size={18} /> Count take as remembered
                  </Button>
                )}
              {data.history[0].session_id && (
                <LearningStaves
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
                              if (data.pending_at && !(await run("/pause")))
                                return;
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
                              if (data.pending_at && !(await run("/pause")))
                                return;
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
                  {result.error_count - 24} further differences. Work on a
                  smaller chunk to review them individually.
                </p>
              )}
              {data.history[0].session_id && (
                <a href={`/api/sessions/${data.history[0].session_id}/midi`}>
                  Download this attempt’s MIDI
                </a>
              )}
            </div>
          )}
          {rule && (
            <form
              className="learning-card"
              onSubmit={async (e) => {
                e.preventDefault();
                if (dictatingReason) return;
                let pitch = rule.pitch;
                try {
                  if (action === "replace") pitch = noteNumber(replacement);
                } catch (error) {
                  onError(error);
                  return;
                }
                if (
                  await run(
                    fixReference ? "/corrections" : "/variants",
                    fixReference
                      ? {
                          note_id: rule.id,
                          replacement,
                          reason,
                        }
                      : {
                          note_id: rule.id,
                          action,
                          pitch,
                          reason,
                        },
                  )
                )
                  setRule(null);
              }}
            >
              <h2>
                {fixReference ? "Fix reference note" : "Overrule"} {rule.name}{" "}
                in measure {rule.measure}
              </h2>
              <p>
                {fixReference
                  ? "Correct this exact note occurrence in the local Learning reference. Future attempts and staff comparisons will use the corrected pitch. The source PDF and old takes remain unchanged."
                  : "This changes only this note occurrence in your personal Learning edition. The printed score and original reference remain intact."}{" "}
                The affected chunk and its later connections will need fresh
                attempts.
              </p>
              {!fixReference && (
                <label>
                  Personal choice
                  <select
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                  >
                    <option value="omit">Omit this note</option>
                    <option value="replace">Play a different note</option>
                  </select>
                </label>
              )}
              {action === "replace" && (
                <label>
                  Replacement note
                  <input
                    required
                    value={replacement}
                    onChange={(e) => setReplacement(e.target.value)}
                    placeholder="e.g. F#4"
                  />
                </label>
              )}
              {action === "replace" && (
                <div
                  className="learning-note-suggestions"
                  role="group"
                  aria-label="Nearby replacement notes"
                >
                  <span>Nearby pitches</span>
                  <div>
                    {[-2, -1, 1, 2]
                      .map((offset) => rule.pitch + offset)
                      .filter((pitch) => pitch >= 0 && pitch <= 127)
                      .map((pitch) => (
                        <Button
                          key={pitch}
                          type="button"
                          disabled={busy}
                          aria-label={`Use ${noteName(pitch)} as replacement`}
                          aria-pressed={replacement === noteName(pitch)}
                          onClick={() => setReplacement(noteName(pitch))}
                        >
                          {noteName(pitch)}
                        </Button>
                      ))}
                  </div>
                </div>
              )}
              <label>
                Reason
                <textarea
                  required
                  disabled={dictatingReason || busy}
                  maxLength={1000}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder={
                    fixReference
                      ? "For example: the printed score restores E flat here."
                      : "For example: omit this inner tone to fit my hand."
                  }
                />
              </label>
              <ReasonDictation
                key={`${rule.id}:${fixReference}`}
                disabled={busy}
                onText={setReason}
                onActiveChange={setDictatingReason}
              />
              <div className="learning-controls">
                <Button
                  className="primary"
                  disabled={busy || dictatingReason || !reason.trim()}
                  type="submit"
                >
                  {fixReference
                    ? "Save reference correction"
                    : "Save personal note rule"}
                </Button>
                <Button type="button" onClick={() => setRule(null)}>
                  Cancel
                </Button>
              </div>
            </form>
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
          <div className="learning-card">
            <div className="section-heading">
              <h2>Your chunk map</h2>
              <Button
                disabled={busy || !!data.active || !!data.pending_at}
                onClick={() => {
                  setConfig({ ...data.profile.config });
                  setChunkText(
                    data.profile.chunks
                      .map((c) => `${c.start}-${c.end}`)
                      .join(", "),
                  );
                  setEditing(!editing);
                }}
              >
                Edit routine & chunks
              </Button>
            </div>
            <div className="learning-chunks">
              <Button
                className={`learning-chunk learning-chunk-review ${data.review.active && target?.start === 0 && target?.end === reviewEnd ? "current" : ""}`}
                disabled={
                  busy ||
                  editing ||
                  !!rule ||
                  !data.ready ||
                  !!data.active ||
                  reviewEnd === null
                }
                title="Recall the piece from the pickup through this point. Your learning position and streak are kept."
                onClick={() =>
                  void run("/review", { include_current: includeCurrent })
                }
              >
                <RotateCcw size={16} />
                <span>
                  {includeCurrent
                    ? "Review through current chunk"
                    : "Review all learned"}
                  <small>
                    {reviewEnd === null
                      ? "No learned chunks yet"
                      : range(0, reviewEnd)}
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
                    Reviewing measures{" "}
                    {target && range(target.start, target.end)}. Your learning
                    position and streak are kept.
                  </p>
                </>
              ) : (
                <>
                  <p>
                    {data.review.learned_end !== null
                      ? `Learned so far: ${range(0, data.review.learned_end)}.`
                      : "No completed hidden-recall chunks yet."}
                  </p>
                  <label className="learning-checkbox">
                    <input
                      type="checkbox"
                      checked={includeCurrent}
                      onChange={(event) =>
                        setIncludeCurrent(event.target.checked)
                      }
                    />
                    Include the current chunk
                  </label>
                </>
              )}
              <details>
                <summary>Future review plans</summary>
                <p>
                  Learning opens in review mode through your last learned chunk
                  after restarting Studio. Press Start review when ready, or
                  Return to learning to continue your assignment. Spaced review
                  scheduling is planned.
                </p>
              </details>
            </div>
            {editing && config && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    const chunks = chunkText.split(",").map((text) => {
                      const match = /^\s*(\d+)\s*-\s*(\d+)\s*$/.exec(text);
                      if (!match)
                        throw new Error(
                          "Use comma-separated ranges, such as 0-2, 3-4.",
                        );
                      const start = Number(match[1]),
                        end = Number(match[2]);
                      return {
                        start,
                        end,
                        focus:
                          data.profile.chunks.find(
                            (c) => c.start <= start && c.end >= start,
                          )?.focus ||
                          "Study this passage and connect it to the preceding material.",
                      };
                    });
                    if (await run("", { config, chunks }, "PUT"))
                      setEditing(false);
                  } catch (error) {
                    onError(error);
                  }
                }}
              >
                <div className="learning-config">
                  {(["visible", "hidden", "connections"] as const).map(
                    (key) => (
                      <label key={key}>
                        {key === "visible"
                          ? "Visible repetitions"
                          : key === "hidden"
                            ? "Hidden repetitions"
                            : "Connection repetitions"}
                        <input
                          type="number"
                          min={1}
                          max={20}
                          required
                          value={config[key]}
                          onChange={(e) =>
                            setConfig({
                              ...config,
                              [key]: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                    ),
                  )}
                </div>
                <label className="learning-checkbox">
                  <input
                    type="checkbox"
                    checked={config.auto_restart_on_mistake}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        auto_restart_on_mistake: e.target.checked,
                      })
                    }
                  />
                  Automatically restart takes on mistakes
                </label>
                <p className="muted">
                  Restarts after a definite pitch or note-order mismatch once
                  all keys are released. Pauses and unfinished passages do not
                  trigger a restart. MIDI is saved and your streak stays
                  unchanged.
                </p>
                <label className="learning-checkbox">
                  <input
                    type="checkbox"
                    checked={config.auto_finish}
                    onChange={(e) =>
                      setConfig({ ...config, auto_finish: e.target.checked })
                    }
                  />
                  Automatically finish a complete correct attempt
                </label>
                <label className="learning-checkbox">
                  <input
                    type="checkbox"
                    checked={config.auto_continue}
                    onChange={(e) =>
                      setConfig({ ...config, auto_continue: e.target.checked })
                    }
                  />
                  Start the next attempt after a two-second review
                </label>
                <label>
                  Chunk ranges (0 is the pickup)
                  <textarea
                    required
                    value={chunkText}
                    onChange={(e) => setChunkText(e.target.value)}
                  />
                </label>
                <p>
                  Cover every measure once, in order. Keep boundaries within
                  these sections: 0–8, 9–16, 17–25, 26–35, 36–43, 44–49.
                  Changing chunks restarts progression and preserves attempt
                  history. Changing repetition settings restarts the current
                  streak.
                </p>
                <div className="learning-controls">
                  <Button disabled={busy} className="primary" type="submit">
                    Save routine
                  </Button>
                  <Button type="button" onClick={() => setEditing(false)}>
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </div>
          <details className="learning-card">
            <summary>Lesson analysis & edition evidence</summary>
            <p>
              {data.lesson.reviewer}. {data.lesson.scope}
            </p>
            <p>
              The plan uses two-measure chunks for the familiar opening
              patterns, single measures through the changing middle, then short
              return and coda groups. Similar passages are learned as separate
              occurrences; differences are not assumed away.
            </p>
            <p>
              Each chunk receives visible study and hidden recall, then section
              connections. Completed sections are cumulatively connected from
              the pickup.
            </p>
            <p>
              Every new proper Learning piece requires an in-depth model
              analysis and edition review. Automatic chunk proposals, if added,
              must remain flagged provisional.
            </p>
            <a href="/api/learning/e25-1/reference" download>
              Download the full reviewed digital counterpart and correction log
            </a>
          </details>
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
                              ? "needs another attempt"
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
              Restart learning from the pickup
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
