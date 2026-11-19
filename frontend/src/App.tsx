import {
  BookOpen,
  ChartNoAxesCombined,
  ChevronRight,
  Circle,
  Eye,
  GraduationCap,
  History,
  LockKeyhole,
  Maximize,
  Minimize,
  Music2,
  Piano,
  Power,
  Settings as SettingsIcon,
  Sprout,
  Square,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Learning } from "./Learning";
import { ProgressHistory } from "./ProgressHistory";
import { TouchButton } from "./TouchButton";
import { VoiceControl } from "./VoiceControl";
import {
  api,
  clock,
  json,
  upload,
  type Piece,
  type Session,
  type Settings,
  type Volume,
} from "./api";
import { Metric } from "./components/AppPrimitives";
import { AppDialogs } from "./dialogs/AppDialogs";
import { AnalysisPage } from "./pages/AnalysisPage";
import { LibraryPage } from "./pages/LibraryPage";
import { PracticePage } from "./pages/PracticePage";
import { ScoreCertificationPage } from "./pages/ScoreCertificationPage";
import type { LessonChoice } from "./learning/types";
import { SessionsPage } from "./pages/SessionsPage";
import { preloadScore } from "./pdfCache";
import { resolveVoiceCommand } from "./voiceCommands";

import type { SessionSummary, Status } from "./appTypes";
import { useAppStatus } from "./hooks/useAppStatus";
const defaults: Settings = {
  preferred_device: "",
  pedal_enabled: false,
  swipe: true,
  pinch: true,
  double_tap: true,
  tap_overlay: false,
  auto_hide: false,
};
const nav = [
  { name: "Practice", icon: Piano },
  { name: "Learning", icon: GraduationCap },
  { name: "Library", icon: BookOpen },
  { name: "Sessions", icon: History },
  { name: "Analysis", icon: ChartNoAxesCombined },
  { name: "Progress", icon: Sprout },
];
export function App() {
  const [sessionGroup, setSessionGroup] = useState<string | null>(null);
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [recordMidi, setRecordMidi] = useState(true);
  const [recordMicrophone, setRecordMicrophone] = useState(true);
  const [microphoneDevice, setMicrophoneDevice] = useState("default");
  const [libraryView, setLibraryView] = useState<"scores" | "recordings">(
    "scores",
  );
  const [recordingPiece, setRecordingPiece] = useState<string | null>(null);
  const [libraryPiece, setLibraryPiece] = useState<Piece | null>(null);
  const [lessons, setLessons] = useState<LessonChoice[]>([]);
  const [certification, setCertification] = useState<{
    pieceId: string;
    back: string;
  } | null>(null);
  const [reviewSegment, setReviewSegment] = useState<string | null>(null);
  const [learningPieceId, setLearningPieceId] = useState(
    localStorage.getItem("chopin-learning-piece") || "e25-1",
  );
  const [tab, setTabState] = useState(
      localStorage.getItem("chopin-learning-piece") ? "Learning" : "Practice",
    ),
    [pieces, setPieces] = useState<Piece[]>([]),
    [volumes, setVolumes] = useState<Volume[]>([]),
    [sessions, setSessions] = useState<Session[]>([]),
    [pieceId, setPieceId] = useState<string | null>(
      localStorage.getItem("chopin-piece"),
    );
  const [scoreFullscreenHost, setScoreFullscreenHost] =
    useState<HTMLElement | null>(null);
  const [settings, setSettings] = useState<Settings>(defaults),
    [modal, setModal] = useState<
      "settings" | "stop" | "edit" | "shutdown" | null
    >(null),
    [service, setService] = useState<"running" | "stopping" | "stopped">(
      "running",
    ),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("All pieces"),
    [search, setSearch] = useState(""),
    [edit, setEdit] = useState<Piece | null>(null),
    [selectedSession, setSelectedSession] = useState<Session | null>(null),
    [summary, setSummary] = useState<SessionSummary | null>(null),
    [full, setFull] = useState(false),
    [hidden, setHidden] = useState(false),
    [command, setCommand] = useState<{
      actions?: { action: string }[];
      id: number;
      action: string;
      page?: number;
      piece_id?: string;
    } | null>(null);
  const [automaticCommand, setAutomaticCommand] = useState<{
    id: number;
    action: string;
    page?: number;
    piece_id?: string;
  } | null>(null);
  const commandAfter = useRef(0),
    midiImport = useRef<HTMLInputElement>(null),
    pdfImport = useRef<HTMLInputElement>(null),
    importVolume = useRef("");
  const piece = pieces.find((p) => p.id === pieceId) || null,
    volume = volumes.find((v) => v.id === piece?.volume_id);
  useEffect(() => {
    if (volume?.filename)
      void preloadScore(volume.id, volume.filename).catch(() => {});
  }, [volume?.id, volume?.filename]);
  const fail = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  const setTab = (next: string) => {
    if (next === "Sessions") setCleanupOpen(false);
    if (tab === "Learning" && next !== "Learning") {
      void api(`/learning/${learningPieceId}/pause`, { method: "POST" })
        .then(() => setTabState(next))
        .catch(fail);
    } else setTabState(next);
  };
  const openCertification = (pieceId: string) => {
    setCertification({
      pieceId,
      back:
        tab === "Score certification"
          ? (certification?.back ?? "Library")
          : tab,
    });
    setHidden(false);
    setTab("Score certification");
  };
  const showScoreLibrary = () => {
    setLibraryView("scores");
    setLibraryPiece(null);
    setTab("Library");
  };
  const certificationPiece = pieces.find(
    (item) => item.id === certification?.pieceId,
  );
  const refresh = async () => {
    const [library, saved] = await Promise.all([
      api<{ pieces: Piece[]; volumes: Volume[] }>("/library"),
      api<Session[]>("/sessions"),
    ]);
    setPieces(library.pieces);
    setVolumes(library.volumes);
    setSessions(saved);
  };
  const { status, setStatus } = useAppStatus(
    service,
    setService,
    setError,
    refresh,
    fail,
  );
  useEffect(() => {
    if (service !== "running") return;
    void Promise.all([
      refresh(),
      api<Settings>("/settings").then(setSettings),
      api<{ pieces: LessonChoice[] }>("/learning").then((catalogue) =>
        setLessons(catalogue.pieces),
      ),
    ]).catch(fail);
  }, [service]);
  useEffect(() => {
    if (service !== "stopping") return;
    let live = true;
    const id = setInterval(() => {
      fetch("/api/status", { signal: AbortSignal.timeout(2000) })
        .then((response) => {
          if (!response.ok && live)
            setError(
              "Could not verify shutdown. Relaunch Chopin Studio to check the service.",
            );
        })
        .catch((e: unknown) => {
          if (!live) return;
          if (e instanceof DOMException && e.name === "TimeoutError") {
            setError(
              "The service is taking longer to stop. Please wait before closing this window.",
            );
          } else {
            setError("");
            setService("stopped");
          }
        });
    }, 700);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [service]);
  useEffect(() => {
    if (
      service === "stopped" &&
      new URLSearchParams(window.location.search).get("desktop") === "1"
    ) {
      window.close();
    }
  }, [service]);
  useEffect(() => {
    if (service !== "running") return;
    const id = setInterval(() => {
      api<{ id: number; action: string }[]>(
        `/page-commands?after=${commandAfter.current}`,
      )
        .then((commands) => {
          const actions = commands.filter(
            (c) => c.action !== "toggle_controls",
          );
          for (const c of commands) {
            commandAfter.current = c.id;
            if (c.action === "toggle_controls") setHidden((x) => !x);
          }
          if (actions.length)
            setCommand({
              id: actions[actions.length - 1].id,
              action: "batch",
              actions,
            });
        })
        .catch(() => {});
    }, 180);
    return () => clearInterval(id);
  }, [service]);
  useEffect(() => {
    const handler = () => {
      setFull(document.fullscreenElement === document.documentElement);
      if (
        !document.fullscreenElement ||
        document.fullscreenElement === document.documentElement
      )
        setHidden(false);
    };
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);
  useEffect(() => {
    if (
      settings.auto_hide &&
      status?.active &&
      !status.certification_piece_id &&
      tab === "Practice" &&
      !full &&
      !scoreFullscreenHost
    ) {
      const id = setTimeout(() => setHidden(true), 10000);
      return () => clearTimeout(id);
    }
  }, [
    settings.auto_hide,
    status?.active,
    status?.certification_piece_id,
    tab,
    full,
    scoreFullscreenHost,
  ]);
  useEffect(() => {
    if (service !== "running") return;
    const handler = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "r" && e.ctrlKey && !e.repeat) {
        e.preventDefault();
        if (status?.certification_piece_id) {
          if (tab !== "Score certification")
            openCertification(status.certification_piece_id);
        } else if (status?.active) setModal("stop");
        else if (tab !== "Score certification") void record();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [status?.active, status?.certification_piece_id, service, tab]);
  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (!hidden || tab !== "Practice") return;
    const bar = document.querySelector<HTMLDivElement>(".floating-status");
    if (!bar) return;
    const reserve = () =>
      document.documentElement.style.setProperty(
        "--practice-controls-space",
        `${Math.ceil(bar.getBoundingClientRect().height) + 40}px`,
      );
    const observer = new ResizeObserver(reserve);
    observer.observe(bar);
    reserve();
    return () => {
      observer.disconnect();
      document.documentElement.style.removeProperty(
        "--practice-controls-space",
      );
    };
  }, [hidden, tab]);
  const record = (microphoneOverride = recordMicrophone) =>
    run(async () => {
      await api("/live/context", json("PUT", { piece_id: piece?.id || null }));
      await api(
        "/record/start",
        json("POST", {
          midi_enabled: recordMidi,
          microphone_enabled: microphoneOverride,
          microphone_device: microphoneDevice,
        }),
      );
      setStatus(await api<Status>("/status"));
      setNotice(
        "Recording started. Everything received is saved, even if you close this window.",
      );
    });
  const stop = () =>
    run(async () => {
      const result = await api<{ id: string }>("/record/stop", {
        method: "POST",
      });
      setModal(null);
      setHidden(false);
      setStatus(await api<Status>("/status"));
      await refresh();
      const list = await api<Session[]>("/sessions");
      setSelectedSession(list.find((s) => s.id === result.id) || null);
      setSummary(null);
      setTab("Sessions");
      setNotice(
        list.find((s) => s.id === result.id)?.status === "incomplete"
          ? "Session saved with capture issues. Review the recording error and retained files."
          : "Session saved. Review Audio cleanup before shutting down: flagged audio, including partial attempts, is removed at application shutdown. Uncertain audio stays for review. Use Keep this audio to protect a take. MIDI is preserved.",
      );
    });
  const shutdown = () =>
    run(async () => {
      await api("/shutdown", {
        method: "POST",
        headers: { "X-Chopin-Shutdown": "1" },
      });
      setModal(null);
      setHidden(false);
      setService("stopping");
    });
  const choose = (p: Piece) => {
    setPieceId(p.id);
    localStorage.setItem("chopin-piece", p.id);
    setTab("Practice");
    setHidden(false);
  };
  const changeAutoTurns = async (enabled: boolean) => {
    const next = {
      ...settings,
      live_auto_turn: enabled,
      live_enabled: enabled || settings.live_enabled,
    };
    await api("/settings", json("PUT", next));
    setSettings(next);
  };
  const clearScore = () => {
    setPieceId(null);
    localStorage.removeItem("chopin-piece");
    setAutomaticCommand(null);
    setCommand(null);
  };
  const inspect = async (
    s: Session,
    target = "Sessions",
    segmentId: string | null = null,
  ) => {
    setReviewSegment(segmentId);
    setSelectedSession(s);
    setSummary(null);
    setTab(target);
    await run(async () =>
      setSummary(await api<SessionSummary>(`/sessions/${s.id}/summary`)),
    );
  };
  const fullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen().catch(fail);
    else
      void document.documentElement
        .requestFullscreen()
        .then(() => setHidden(false))
        .catch(() =>
          setError(
            "Fullscreen is unavailable in this browser. Use its installed-app mode or maximise the window.",
          ),
        );
  };
  const saveSettings = () =>
    run(async () => {
      await api("/settings", json("PUT", settings));
      setModal(null);
      setNotice("Settings saved locally.");
    });
  const openEdit = (p: Piece) => {
    setEdit({ ...p });
    setModal("edit");
  };
  const practiceSessions = sessions.filter((s) => s.source !== "learning");
  const analysisSession =
    selectedSession?.source !== "learning" ? selectedSession : null;
  const total = sessions.reduce((sum, s) => sum + s.duration, 0);

  if (service !== "running")
    return (
      <main className="shutdown-screen">
        <Power size={36} />
        <h1>
          {service === "stopped"
            ? "Chopin Studio is shut down"
            : "Shutting down Chopin Studio…"}
        </h1>
        <p>
          Your recording has been saved.{" "}
          {service === "stopped"
            ? "You can close this window."
            : "Waiting for the local service to stop."}
        </p>
        <p>To start again, click the Chopin Studio application icon.</p>
        {error && <p role="alert">{error}</p>}
      </main>
    );
  return (
    <div
      className={`app ${hidden && tab === "Practice" ? "distraction-free" : ""}`}
    >
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-symbol">♮</div>
          <div>
            Chopin<span>STUDIO</span>
          </div>
        </div>
        <div className="sidebar-label">YOUR PRACTICE SPACE</div>
        <nav>
          {nav.map(({ name, icon: Icon }) => (
            <TouchButton
              key={name}
              className={tab === name ? "active" : ""}
              onClick={() => {
                setTab(name);
                setHidden(false);
              }}
            >
              <Icon size={21} />
              <span>{name}</span>
              {tab === name && <i />}
            </TouchButton>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-note">
            <LockKeyhole size={15} />
            <span>Local. Private. Yours.</span>
          </div>
          <TouchButton onClick={() => setModal("settings")}>
            <SettingsIcon size={20} />
            Settings & devices
          </TouchButton>
          <div className="app-brand">
            CHOPIN STUDIO <span>LOCAL EDITION</span>
          </div>
        </div>
      </aside>
      <VoiceControl
        onCommand={(text) => {
          const result = resolveVoiceCommand(text, pieces);
          if (!result.piece) return result.message;
          choose(result.piece);
          return `Opened ${result.piece.title} Op. ${result.piece.opus}.`;
        }}
      />
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Your studio <ChevronRight size={14} />
            <span>{tab}</span>
          </div>
          <div className="top-actions">
            <TouchButton
              className={`connection ${status?.connected ? "connected" : ""}`}
              onClick={() => setModal("settings")}
            >
              <span className="dot" />
              {status?.connected
                ? "Piano connected"
                : status?.simulation
                  ? "Simulated input"
                  : "No piano connected"}
            </TouchButton>
            <TouchButton
              className="icon-button"
              aria-label="Shut down Chopin Studio"
              title="Shut down Chopin Studio"
              disabled={busy || !status}
              onClick={() => setModal("shutdown")}
            >
              <Power size={19} />
            </TouchButton>
            <TouchButton
              className="icon-button"
              aria-label={full ? "Exit app fullscreen" : "Enter app fullscreen"}
              title="Expand the entire application to fullscreen"
              onClick={fullscreen}
            >
              {full ? <Minimize size={19} /> : <Maximize size={19} />}
              {full ? "Exit app fullscreen" : "App fullscreen"}
            </TouchButton>
          </div>
        </header>
        {error && (
          <div className="banner error" role="alert">
            <span>{error}</span>
            <TouchButton
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              <X size={18} />
            </TouchButton>
          </div>
        )}
        {notice && !hidden && (
          <div className="banner" role="status">
            <span>{notice}</span>
            <TouchButton
              aria-label="Dismiss notification"
              onClick={() => setNotice("")}
            >
              <X size={18} />
            </TouchButton>
          </div>
        )}
        {status?.error && (
          <div className="banner error" role="alert">
            {status.error}
          </div>
        )}
        {status?.active &&
          status.certification_piece_id &&
          (tab !== "Score certification" ||
            certification?.pieceId !== status.certification_piece_id) && (
            <div className="recording-ribbon">
              <span className="record-dot" />
              Score certification recording · {clock(status.duration)}
              <TouchButton
                onClick={() =>
                  openCertification(status.certification_piece_id!)
                }
              >
                Return to score certification
              </TouchButton>
            </div>
          )}
        {status?.active &&
          !status.certification_piece_id &&
          tab !== "Practice" &&
          tab !== "Learning" && (
            <div className="recording-ribbon">
              <span className="record-dot" />
              Recording · {clock(status.duration)}
              <TouchButton
                onClick={() => {
                  setTab("Practice");
                  setHidden(false);
                }}
              >
                Return to practice
              </TouchButton>
              <TouchButton onClick={() => setModal("stop")}>
                Stop session
              </TouchButton>
            </div>
          )}
        {tab === "Practice" ? (
          <PracticePage
            piece={piece}
            setTab={setTab}
            hidden={hidden}
            scoreFullscreenHost={scoreFullscreenHost}
            pieces={pieces}
            settings={settings}
            setSettings={setSettings}
            choose={choose}
            setAutomaticCommand={setAutomaticCommand}
            fail={fail}
            status={status}
            recordMidi={recordMidi}
            busy={busy}
            setRecordMidi={setRecordMidi}
            recordMicrophone={recordMicrophone}
            setRecordMicrophone={setRecordMicrophone}
            microphoneDevice={microphoneDevice}
            setMicrophoneDevice={setMicrophoneDevice}
            record={record}
            changeAutoTurns={changeAutoTurns}
            setScoreFullscreenHost={setScoreFullscreenHost}
            setModal={(next) => {
              if (next === "stop" && status?.certification_piece_id)
                openCertification(status.certification_piece_id);
              else setModal(next);
            }}
            clearScore={clearScore}
            automaticCommand={automaticCommand}
            volume={volume}
            command={command}
            setHidden={setHidden}
          />
        ) : tab === "Score certification" && certificationPiece ? (
          <ScoreCertificationPage
            key={certificationPiece.id}
            piece={certificationPiece}
            volumes={volumes}
            settings={settings}
            recording={status?.active ?? null}
            recordingCertificationPiece={status?.certification_piece_id ?? null}
            saving={!!status?.saving}
            onBack={() => setTab(certification?.back ?? "Library")}
            onLibrary={showScoreLibrary}
          />
        ) : tab === "Learning" ? (
          <Learning
            onPieceChange={setLearningPieceId}
            pieces={pieces}
            volumes={volumes}
            settings={settings}
            onError={fail}
            onLibrary={showScoreLibrary}
            onCertification={openCertification}
          />
        ) : tab === "Library" ? (
          <LibraryPage
            libraryView={libraryView}
            setLibraryView={setLibraryView}
            pieces={pieces}
            recordingPiece={recordingPiece}
            setRecordingPiece={setRecordingPiece}
            setLibraryPiece={setLibraryPiece}
            setCleanupOpen={setCleanupOpen}
            inspect={inspect}
            libraryPiece={libraryPiece}
            setReviewSegment={setReviewSegment}
            search={search}
            setSearch={setSearch}
            filter={filter}
            setFilter={setFilter}
            volumes={volumes}
            run={run}
            refresh={refresh}
            choose={choose}
            openEdit={openEdit}
            learningPieceIds={lessons.map((lesson) => lesson.piece_id)}
            certificationPieceIds={lessons
              .filter((lesson) => lesson.certification_available)
              .map((lesson) => lesson.piece_id)}
            onCertification={openCertification}
            busy={busy}
            setLearningPieceId={setLearningPieceId}
            setTab={setTab}
            importVolume={importVolume}
            pdfImport={pdfImport}
            fail={fail}
          />
        ) : tab === "Sessions" ? (
          <SessionsPage
            midiImport={midiImport}
            setCleanupOpen={setCleanupOpen}
            cleanupOpen={cleanupOpen}
            fail={fail}
            refresh={refresh}
            inspect={inspect}
            selectedSession={selectedSession}
            libraryView={libraryView}
            setTab={setTab}
            libraryPiece={libraryPiece}
            setSelectedSession={setSelectedSession}
            setSummary={setSummary}
            sessionGroup={sessionGroup}
            summary={summary}
            busy={busy}
            status={status}
            setReviewSegment={setReviewSegment}
            setNotice={setNotice}
            pieces={pieces}
            reviewSegment={reviewSegment}
            run={run}
            sessions={sessions}
            setSessionGroup={setSessionGroup}
          />
        ) : tab === "Analysis" ? (
          <AnalysisPage
            fail={fail}
            analysisSession={analysisSession}
            sessions={sessions}
            inspect={inspect}
            setSelectedSession={setSelectedSession}
            setReviewSegment={setReviewSegment}
            practiceSessions={practiceSessions}
            setCleanupOpen={setCleanupOpen}
            setTab={setTab}
            busy={busy}
            pieces={pieces}
            reviewSegment={reviewSegment}
          />
        ) : (
          <section className="content">
            <div className="page-heading">
              <div>
                <span className="eyebrow">BUILT ONE SESSION AT A TIME</span>
                <h1>A practice worth returning to.</h1>
                <p>Your history, without a single score for musical quality.</p>
              </div>
            </div>
            <div className="metric-grid">
              <Metric
                label="Saved sessions"
                value={sessions.length.toString()}
              />
              <Metric label="Total recorded time" value={clock(total)} />
              <Metric
                label="Pieces currently learning"
                value={pieces
                  .filter((p) => p.practice_status === "Learning")
                  .length.toString()}
              />
            </div>
            <div className="section-heading">
              <h2>On your music stand</h2>
              <p>
                Mark pieces as Learning in the library. Attributed practice time
                appears after activities are matched or manually identified.
              </p>
            </div>
            <ProgressHistory onError={fail} />
            <div className="learning-list">
              {pieces
                .filter((p) => p.practice_status === "Learning" || p.favourite)
                .map((p) => (
                  <TouchButton
                    className="session-row"
                    key={p.id}
                    onClick={() => choose(p)}
                  >
                    <Music2 />
                    <div>
                      <h3>
                        {p.title} in {p.musical_key}
                      </h3>
                      <p>
                        Op. {p.opus} · {p.practice_status}
                      </p>
                    </div>
                    <ChevronRight />
                  </TouchButton>
                ))}
            </div>
            {!pieces.some(
              (p) => p.practice_status === "Learning" || p.favourite,
            ) && (
              <TouchButton
                className="primary"
                onClick={() => setTab("Library")}
              >
                Explore your repertoire
                <ChevronRight size={18} />
              </TouchButton>
            )}
          </section>
        )}
      </main>
      {hidden && tab === "Practice" && (
        <div className="floating-status">
          <span className={status?.active ? "record-dot" : "ready-dot"} />
          {status?.active
            ? `Recording ${clock(status.duration)}`
            : "Practice mode"}
          <TouchButton onClick={() => setHidden(false)}>
            <Eye size={18} />
            Show controls
          </TouchButton>
          {!status?.active && (
            <TouchButton
              disabled={
                busy ||
                !status ||
                status.saving ||
                (!recordMidi && !recordMicrophone)
              }
              onClick={() => void record()}
            >
              <Circle size={16} fill="currentColor" />
              Record session
            </TouchButton>
          )}
          {status?.active && (
            <TouchButton
              aria-label="Stop session"
              onClick={() => {
                if (status.certification_piece_id)
                  openCertification(status.certification_piece_id);
                else setModal("stop");
              }}
            >
              <Square size={16} />
              Stop
            </TouchButton>
          )}
          <TouchButton
            onClick={() => setCommand({ id: Date.now(), action: "toggle_two" })}
          >
            One / two pages
          </TouchButton>
          {piece && (
            <TouchButton onClick={clearScore}>
              <X size={18} />
              Clear score
            </TouchButton>
          )}
          <TouchButton onClick={() => setModal("settings")}>
            Options
          </TouchButton>
          {full && (
            <TouchButton aria-label="Exit app fullscreen" onClick={fullscreen}>
              <Minimize size={18} />
            </TouchButton>
          )}
        </div>
      )}
      <input
        hidden
        ref={midiImport}
        type="file"
        accept=".mid,.midi,.csv"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f)
            void run(async () => {
              await upload("/import/midi", f);
              await refresh();
              setNotice(
                "Imported successfully. The original file is preserved.",
              );
              setTab("Sessions");
              setSelectedSession(null);
            });
          e.target.value = "";
        }}
      />
      <input
        hidden
        ref={pdfImport}
        type="file"
        accept=".pdf"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f)
            void run(async () => {
              await upload(`/volumes/${importVolume.current}/pdf`, f);
              await refresh();
              setNotice(
                "PDF imported. Set the piece page ranges using its edit button.",
              );
            });
          e.target.value = "";
        }}
      />
      {modal && (
        <AppDialogs
          scoreFullscreenHost={scoreFullscreenHost}
          modal={modal}
          busy={busy}
          setModal={setModal}
          error={error}
          shutdown={shutdown}
          stop={stop}
          edit={edit}
          run={run}
          refresh={refresh}
          setEdit={setEdit}
          volumes={volumes}
          settings={settings}
          setSettings={setSettings}
          status={status}
          midiImport={midiImport}
          sessions={sessions}
          saveSettings={saveSettings}
        />
      )}
      {busy && (
        <div className="busy-indicator" role="status">
          Working…
        </div>
      )}
    </div>
  );
}
