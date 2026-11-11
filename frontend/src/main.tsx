import { RecordingCleanup, SessionDeleteButton } from "./RecordingCleanup";
import { CompareTakes } from "./CompareTakes";
import { PracticeReview } from "./PracticeReview";
import { PieceSessions } from "./PieceSessions";
import { References } from "./References";
import { LivePanel } from "./LivePanel";
import { ProgressHistory } from "./ProgressHistory";
import { TouchButton } from "./TouchButton";
import { VoiceControl } from "./VoiceControl";
import { resolveVoiceCommand } from "./voiceCommands";
import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  Circle,
  Square,
  Settings as SettingsIcon,
  Piano,
  History,
  ChartNoAxesCombined,
  Sprout,
  ChevronRight,
  Upload,
  Star,
  X,
  Maximize,
  Minimize,
  SlidersHorizontal,
  ArrowLeft,
  Check,
  Cable,
  RefreshCw,
  LockKeyhole,
  Eye,
  Music2,
  Download,
  FileText,
  CircleHelp,
  Volume2,
  Power,
} from "lucide-react";
import {
  api,
  json,
  upload,
  clock,
  type Piece,
  type Volume,
  type Session,
  type Settings,
} from "./api";
import { Score } from "./Score";
import { preloadScore } from "./pdfCache";
import "./style.css";

type Status = {
  active: string | null;
  duration: number;
  events: number;
  error: string | null;
  devices: string[];
  connected: string | null;
  device_error: string | null;
  notes: Record<string, number>;
  pedals: Record<string, number>;
  recent: { at: number; message: string }[];
  queue_depth: number;
  last_event_age: number | null;
  simulation: boolean;
  event_rate: number;
  saving: boolean;
  shutting_down: boolean;
  midi_enabled?: boolean;
  microphone_enabled?: boolean;
};
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
  { name: "Library", icon: BookOpen },
  { name: "Sessions", icon: History },
  { name: "Analysis", icon: ChartNoAxesCombined },
  { name: "Progress", icon: Sprout },
];
function App() {
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [recordMidi, setRecordMidi] = useState(true);
  const [recordMicrophone, setRecordMicrophone] = useState(true);
  const [microphoneDevice, setMicrophoneDevice] = useState("default");
  const [libraryPiece, setLibraryPiece] = useState<Piece | null>(null);
  const [reviewSegment, setReviewSegment] = useState<string | null>(null);
  const [tab, setTab] = useState("Practice"),
    [pieces, setPieces] = useState<Piece[]>([]),
    [volumes, setVolumes] = useState<Volume[]>([]),
    [sessions, setSessions] = useState<Session[]>([]),
    [pieceId, setPieceId] = useState<string | null>(
      localStorage.getItem("chopin-piece"),
    );
  const [scoreFullscreenHost, setScoreFullscreenHost] =
    useState<HTMLElement | null>(null);
  const [status, setStatus] = useState<Status | null>(null),
    [settings, setSettings] = useState<Settings>(defaults),
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
    [summary, setSummary] = useState<any>(null),
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
  const refresh = async () => {
    const [library, saved] = await Promise.all([
      api("/library"),
      api<Session[]>("/sessions"),
    ]);
    setPieces(library.pieces);
    setVolumes(library.volumes);
    setSessions(saved);
  };
  useEffect(() => {
    if (service !== "running") return;
    void Promise.all([
      refresh(),
      api<Settings>("/settings").then(setSettings),
    ]).catch(fail);
    let live = true;
    let previousRecording: string | null = null;
    const poll = async () => {
      try {
        const s = await api<Status>("/status", {
          headers: { "X-Chopin-Frontend": "1" },
        });
        if (live) {
          if (previousRecording && previousRecording !== s.active)
            void refresh().catch(fail);
          previousRecording = s.active;
          setStatus(s);
          if (s.shutting_down) setService("stopping");
          setError((e) =>
            e ===
            "Local service unavailable. Recording may still be running; reconnect before starting another session."
              ? ""
              : e,
          );
        }
      } catch {
        if (live)
          setError(
            "Local service unavailable. Recording may still be running; reconnect before starting another session.",
          );
      }
    };
    void poll();
    const id = setInterval(poll, 700);
    return () => {
      live = false;
      clearInterval(id);
    };
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
      tab === "Practice" &&
      !full &&
      !scoreFullscreenHost
    ) {
      const id = setTimeout(() => setHidden(true), 10000);
      return () => clearTimeout(id);
    }
  }, [settings.auto_hide, status?.active, tab, full, scoreFullscreenHost]);
  useEffect(() => {
    if (service !== "running") return;
    const handler = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "r" && e.ctrlKey && !e.repeat) {
        e.preventDefault();
        if (status?.active) setModal("stop");
        else void record();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [status?.active, service]);
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
      setStatus(await api("/status"));
      setNotice(
        "Recording started. Everything received is saved, even if you close this window.",
      );
    });
  const stop = () =>
    run(async () => {
      const result = await api("/record/stop", { method: "POST" });
      setModal(null);
      setHidden(false);
      setStatus(await api("/status"));
      await refresh();
      const list = await api<Session[]>("/sessions");
      setSelectedSession(list.find((s) => s.id === result.id) || null);
      setSummary(null);
      setTab("Sessions");
      setCleanupOpen(true);
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
  const inspect = async (s: Session, target = "Sessions") => {
    setReviewSegment(null);
    setSelectedSession(s);
    setSummary(null);
    setTab(target);
    await run(async () => setSummary(await api(`/sessions/${s.id}/summary`)));
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
  const total = sessions.reduce((sum, s) => sum + s.duration, 0);
  const filtered = pieces.filter(
    (p) =>
      (filter === "All pieces" ||
        p.genre === filter ||
        p.intent === filter ||
        (filter === "Favourites" && p.favourite) ||
        (filter === "Learning" && p.practice_status === "Learning")) &&
      `${p.title} ${p.opus} ${p.musical_key}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
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
          <div className="version">
            CHOPIN STUDIO <span>0.2 · LOCAL EDITION</span>
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
        {status?.active && tab !== "Practice" && (
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
          <section className="practice">
            <div className="page-heading">
              <div>
                <span className="eyebrow">A LITTLE SPACE FOR GREAT MUSIC</span>
                <h1>Your piano, your pace.</h1>
              </div>
              <div className="date-label">
                {new Date().toLocaleDateString("en-GB", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                })}
              </div>
            </div>
            <div className="practice-workspace">
              <div className="piece-bar">
                <div className="piece-info">
                  <div className="piece-icon">
                    <Music2 size={24} />
                  </div>
                  <div>
                    <h2>
                      {piece
                        ? `${piece.title} in ${piece.musical_key}`
                        : "An open invitation to practise"}
                    </h2>
                    <p>
                      {piece
                        ? `Frédéric Chopin · Op. ${piece.opus} · ${piece.preferred_edition} edition`
                        : "Record freely. Select a score whenever you like."}
                    </p>
                  </div>
                </div>
                <TouchButton
                  className="secondary"
                  onClick={() => setTab("Library")}
                >
                  <BookOpen size={18} />
                  {piece ? "Change piece" : "Choose a piece"}
                </TouchButton>
              </div>
              <LivePanel
                overlay={hidden || !!scoreFullscreenHost}
                portalTarget={scoreFullscreenHost}
                currentPiece={piece}
                pieces={pieces}
                settings={settings}
                onSettings={setSettings}
                onChoose={choose}
                onPage={setAutomaticCommand}
                onError={fail}
              />
              <div className="chart-panel" aria-label="Recording sources">
                <h2>Recording sources</h2>
                <label className="toggle-row">
                  Record cable MIDI
                  <input
                    type="checkbox"
                    checked={
                      status?.active ? !!status.midi_enabled : recordMidi
                    }
                    disabled={!!status?.active || busy}
                    onChange={(e) => setRecordMidi(e.target.checked)}
                  />
                </label>
                <label className="toggle-row">
                  Record laptop microphone
                  <input
                    type="checkbox"
                    checked={
                      status?.active
                        ? !!status.microphone_enabled
                        : recordMicrophone
                    }
                    disabled={!!status?.active || busy}
                    onChange={(e) => setRecordMicrophone(e.target.checked)}
                  />
                </label>
                {recordMicrophone && (
                  <label>
                    Microphone input (system default or ALSA device)
                    <input
                      value={microphoneDevice}
                      disabled={!!status?.active || busy}
                      onChange={(e) => setMicrophoneDevice(e.target.value)}
                    />
                  </label>
                )}
                {!status?.active && (
                  <TouchButton
                    className="record-button"
                    disabled={busy || !status || status.saving}
                    onClick={() => {
                      setRecordMicrophone(true);
                      void record(true);
                    }}
                  >
                    <Volume2 size={18} />
                    {recordMidi
                      ? "Record microphone + MIDI"
                      : "Record microphone"}
                  </TouchButton>
                )}
                <p className="muted">
                  Choose sources before starting. Microphone uses the laptop’s
                  system input and saves lossless mono audio locally. Select the
                  built-in microphone in system sound settings. About 5.76
                  MB/min before FLAC compression. With microphone on, unplugging
                  MIDI does not stop the session.
                </p>
              </div>
              <Score
                onAutoTurnChange={changeAutoTurns}
                onFullscreenHost={setScoreFullscreenHost}
                onClear={clearScore}
                automaticCommand={automaticCommand}
                piece={piece}
                volume={volume}
                settings={settings}
                onLibrary={() => setTab("Library")}
                command={command}
                onError={fail}
                onToggle={() => setHidden((h) => !h)}
              />
              <div className="recorder">
                <div className="recording-status">
                  <span
                    className={status?.active ? "record-dot" : "ready-dot"}
                  />
                  <div>
                    <strong>
                      {status?.active
                        ? "Session recording"
                        : "Ready when you are"}
                    </strong>
                    <span>
                      {status?.active
                        ? `${status.events.toLocaleString()} events captured · journal saving continuously`
                        : "No piece selection or filename needed"}
                    </span>
                  </div>
                </div>
                <div className="record-controls">
                  <span className="timer">{clock(status?.duration || 0)}</span>
                  {status?.active ? (
                    <TouchButton
                      className="stop-button"
                      disabled={busy}
                      onClick={() => setModal("stop")}
                    >
                      <Square size={17} fill="currentColor" />
                      Stop session
                    </TouchButton>
                  ) : (
                    <TouchButton
                      className="record-button"
                      disabled={
                        busy ||
                        !status ||
                        status.saving ||
                        (!recordMidi && !recordMicrophone)
                      }
                      onClick={() => void record()}
                    >
                      <Circle size={18} fill="currentColor" />
                      Record session
                    </TouchButton>
                  )}
                  <TouchButton
                    className="icon-button"
                    aria-label="Hide practice controls"
                    onClick={() => setHidden(true)}
                  >
                    <Eye size={20} />
                  </TouchButton>
                </div>
              </div>
            </div>
            <div className="practice-foot">
              <span>
                <span className="tiny-dot" />
                Original recordings preserved · No automatic uploads
              </span>
              <TouchButton onClick={() => setModal("settings")}>
                Touch & pedal controls
                <SlidersHorizontal size={15} />
              </TouchButton>
            </div>
          </section>
        ) : tab === "Library" ? (
          <section className="content">
            <div className="page-heading">
              <div>
                <span className="eyebrow">A LIFETIME OF CHOPIN</span>
                <h1>Your score library.</h1>
                <p>Individual pieces. Familiar editions. All in one place.</p>
              </div>
              <TouchButton
                className="secondary"
                onClick={() =>
                  document
                    .getElementById("volume-imports")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
              >
                <Upload size={19} />
                Import a score
              </TouchButton>
            </div>
            {libraryPiece ? (
              <PieceSessions
                key={libraryPiece.id}
                piece={libraryPiece}
                onClose={() => setLibraryPiece(null)}
                onOpen={(s, segmentId) => {
                  void inspect(s);
                  setReviewSegment(segmentId);
                }}
              />
            ) : (
              <>
                <div className="search-row">
                  <input
                    aria-label="Search pieces"
                    placeholder="Search a title, opus or key…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <select
                    aria-label="Filter library"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    {[
                      "All pieces",
                      "Favourites",
                      "Learning",
                      "Nocturnes",
                      "Études",
                      "Preludes",
                      "Waltzes",
                      "Polonaises",
                      "Mazurkas",
                      "Impromptus",
                      "Sonatas",
                      "Ballades",
                      "Review",
                      "Next",
                      "Planned",
                      "Dream",
                    ].map((f) => (
                      <option key={f}>{f}</option>
                    ))}
                  </select>
                </div>
                <div className="piece-grid">
                  {filtered.map((p) => {
                    const v = volumes.find((v) => v.id === p.volume_id);
                    return (
                      <React.Fragment key={p.id}>
                        {filtered.findIndex((x) => x.genre === p.genre) ===
                          filtered.indexOf(p) && (
                          <h2 className="genre-heading">Chopin / {p.genre}</h2>
                        )}
                        <article className="piece-card" data-piece-id={p.id}>
                          <div className="card-top">
                            <span className="eyebrow">{p.genre}</span>
                            <TouchButton
                              aria-label={`Favourite ${p.title} Op. ${p.opus}`}
                              className="icon-button"
                              onClick={() =>
                                void run(async () => {
                                  await api(
                                    `/pieces/${p.id}`,
                                    json("PUT", {
                                      ...p,
                                      favourite: !p.favourite,
                                    }),
                                  );
                                  await refresh();
                                })
                              }
                            >
                              <Star
                                size={20}
                                fill={p.favourite ? "#b39864" : "none"}
                              />
                            </TouchButton>
                          </div>
                          <h2>{p.title}</h2>
                          <p className="piece-key">{p.musical_key}</p>
                          <p>{p.catalogue_path}</p>
                          <p className="repertoire-state">
                            {p.intent}
                            {p.mastery != null
                              ? ` · your learning: ${p.mastery}/3`
                              : ""}
                            {p.liking ? ` · ${"+".repeat(p.liking)}` : ""}
                            {p.forgotten ? " · X — largely forgotten" : ""}
                          </p>
                          {p.notes && (
                            <p className="repertoire-note">{p.notes}</p>
                          )}
                          <div className="score-badges">
                            <span className={v?.filename ? "available" : ""}>
                              {v?.filename ? "PDF imported" : "PDF missing"}
                            </span>
                            <span
                              className={p.reference_count ? "available" : ""}
                            >
                              {p.reference_count
                                ? `${p.reference_count} symbolic reference${p.reference_count > 1 ? "s" : ""}`
                                : "No symbolic reference"}
                            </span>
                          </div>
                          <div className="card-buttons">
                            <TouchButton
                              className="primary"
                              onClick={() => choose(p)}
                            >
                              <BookOpen size={18} />
                              Open score
                            </TouchButton>
                            <TouchButton
                              className="icon-button"
                              aria-label={`Edit ${p.title} Op. ${p.opus}`}
                              onClick={() => openEdit(p)}
                            >
                              <SlidersHorizontal size={19} />
                            </TouchButton>
                            <TouchButton
                              className="secondary piece-sessions-button"
                              onClick={() => setLibraryPiece(p)}
                            >
                              <History size={18} />
                              Saved sessions
                            </TouchButton>
                          </div>
                        </article>
                      </React.Fragment>
                    );
                  })}
                </div>
                {!filtered.length && (
                  <p className="empty-message">No pieces match this filter.</p>
                )}
                <div className="section-heading" id="volume-imports">
                  <h2>The Paderewski collection</h2>
                  <p>
                    Import a legally obtained PDF, then set each piece’s PDF
                    page range. No scans are bundled.
                  </p>
                </div>
                <div className="volume-list">
                  {volumes.map((v) => (
                    <div className="volume-row" key={v.id}>
                      <div className="volume-icon">
                        <BookOpen />
                      </div>
                      <div>
                        <strong>{v.title}</strong>
                        <p>
                          {v.filename
                            ? `${v.pages} PDF pages · Stored locally`
                            : "Awaiting your PDF"}{" "}
                          ·{" "}
                          <a href={v.source} target="_blank" rel="noreferrer">
                            Source & attribution ↗
                          </a>
                        </p>
                      </div>
                      <TouchButton
                        className="secondary"
                        onClick={() => {
                          importVolume.current = v.id;
                          pdfImport.current?.click();
                        }}
                      >
                        <Upload size={18} />
                        {v.filename ? "Replace PDF" : "Import PDF"}
                      </TouchButton>
                    </div>
                  ))}
                </div>
                <References
                  pieces={pieces}
                  onError={fail}
                  onChanged={refresh}
                />
              </>
            )}
          </section>
        ) : tab === "Sessions" ? (
          <section className="content">
            <div className="page-heading">
              <div>
                <span className="eyebrow">EVERY HOUR COUNTS</span>
                <h1>Your practice sessions.</h1>
                <p>
                  Keep your MIDI history, clean up audio, or delete accidental
                  sessions.
                </p>
              </div>
              <TouchButton
                className="secondary"
                onClick={() => midiImport.current?.click()}
              >
                <Upload size={19} />
                Import MIDI / CSV
              </TouchButton>
            </div>
            <div className="button-row">
              <TouchButton
                className="secondary"
                onClick={() => setCleanupOpen(!cleanupOpen)}
              >
                {cleanupOpen
                  ? "Hide audio cleanup"
                  : "Audio cleanup · kept & flagged recordings"}
              </TouchButton>
            </div>
            {cleanupOpen && (
              <RecordingCleanup
                onError={fail}
                onChanged={refresh}
                onOpen={(session, id) => {
                  setReviewSegment(id);
                  void inspect(session);
                  setCleanupOpen(false);
                }}
              />
            )}
            {selectedSession ? (
              <>
                {libraryPiece && (
                  <TouchButton
                    className="text-button"
                    onClick={() => {
                      setSelectedSession(null);
                      setSummary(null);
                      setTab("Library");
                    }}
                  >
                    <ArrowLeft size={18} />
                    Back to {libraryPiece.title} saved sessions
                  </TouchButton>
                )}
                <TouchButton
                  className="text-button"
                  onClick={() => {
                    setSelectedSession(null);
                    setSummary(null);
                  }}
                >
                  <ArrowLeft size={18} />
                  All sessions
                </TouchButton>
                <SessionDetail
                  session={selectedSession}
                  summary={summary}
                  onDelete={
                    <SessionDeleteButton
                      session={selectedSession}
                      onError={fail}
                      disabled={busy || !!status?.active || !!status?.saving}
                      onDeleted={async () => {
                        setSelectedSession(null);
                        setSummary(null);
                        setReviewSegment(null);
                        await refresh();
                        setNotice("Session deleted.");
                      }}
                    />
                  }
                  onAnalysis={() => void inspect(selectedSession, "Analysis")}
                />
                <PracticeReview
                  key={selectedSession.id}
                  session={selectedSession}
                  pieces={pieces}
                  onError={fail}
                  initialSegmentId={reviewSegment}
                />
              </>
            ) : sessions.length ? (
              <div className="session-list">
                {sessions.map((s) => (
                  <article key={s.id}>
                    <TouchButton
                      className="session-row"
                      key={s.id}
                      onClick={() => void inspect(s)}
                    >
                      <div className="session-icon">
                        <History size={22} />
                      </div>
                      <div>
                        <h3>{s.name.replaceAll("_", " ")}</h3>
                        <p>
                          {new Date(s.started).toLocaleString()} ·{" "}
                          {s.events.toLocaleString()} events · {s.status}
                        </p>
                        {s.error && <p className="warning-text">{s.error}</p>}
                      </div>
                      <span className="duration">{clock(s.duration)}</span>
                      <ChevronRight size={20} />
                    </TouchButton>
                    <SessionDeleteButton
                      session={s}
                      onError={fail}
                      disabled={busy || !!status?.active || !!status?.saving}
                      onDeleted={refresh}
                    />
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-panel">
                <History size={34} />
                <h2>Your first session starts at the piano.</h2>
                <p>
                  Record freely or import a previous MIDI performance. No
                  recording is created until you choose.
                </p>
                <TouchButton
                  className="primary"
                  onClick={() => setTab("Practice")}
                >
                  Go to practice
                  <ChevronRight size={18} />
                </TouchButton>
              </div>
            )}
          </section>
        ) : tab === "Analysis" ? (
          <section className="content">
            <div className="page-heading">
              <div>
                <span className="eyebrow">LISTEN WITH CURIOSITY</span>
                <h1>A closer look at your playing.</h1>
                <p>
                  Objective MIDI facts, with room for musical interpretation.
                </p>
              </div>
            </div>
            <CompareTakes onError={fail} />
            <select
              aria-label="Select analysis session"
              value={selectedSession?.id || ""}
              onChange={(e) => {
                const s = sessions.find((s) => s.id === e.target.value);
                if (s) void inspect(s, "Analysis");
              }}
            >
              <option value="">Choose a saved session</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            {summary ? (
              <>
                <div className="metric-grid">
                  <Metric
                    label="Note onsets"
                    value={summary.notes.toLocaleString()}
                  />
                  <Metric
                    label="Recording length"
                    value={clock(selectedSession?.duration || 0)}
                  />
                  <Metric
                    label="Seconds with note onsets"
                    value={summary.note_active_seconds.toString()}
                  />
                </div>
                <div className="chart-panel">
                  <span className="eyebrow">VELOCITY OVER TIME</span>
                  <h2>The shape of your touch</h2>
                  <p>
                    MIDI key velocity (0–127), not measured acoustic loudness.
                    Tap a bar for its time and mean value.
                  </p>
                  <div className="velocity-chart">
                    {summary.velocity.map((b: any, i: number) => (
                      <TouchButton
                        key={i}
                        aria-label={`${clock(b.t)}, mean velocity ${Math.round(b.mean)}`}
                        style={{
                          height: `${Math.max(3, (b.mean / 127) * 100)}%`,
                        }}
                        onClick={() =>
                          setNotice(
                            `${clock(b.t)} · Mean velocity ${Math.round(b.mean)} · Range ${b.min}–${b.max} · ${b.notes} note onsets`,
                          )
                        }
                      />
                    ))}
                  </div>
                  <div className="chart-axis">
                    <span>00:00</span>
                    <span>{clock(selectedSession?.duration || 0)}</span>
                  </div>
                </div>
                <div className="chart-panel">
                  <span className="eyebrow">ORIGINAL CC64 VALUES</span>
                  <h2>Damper pedal</h2>
                  {summary.pedals.length ? (
                    <div className="pedal-chart">
                      {summary.pedals.map((p: any, i: number) => (
                        <TouchButton
                          key={i}
                          aria-label={`Pedal ${p.value} at ${clock(p.t)}`}
                          style={{
                            left: `${(100 * p.t) / (selectedSession?.duration || 1)}%`,
                            bottom: `${(p.value / 127) * 80}%`,
                          }}
                          onClick={() =>
                            setNotice(
                              `${clock(p.t)} · Damper CC64 = ${p.value}`,
                            )
                          }
                        />
                      ))}
                    </div>
                  ) : (
                    <p>No damper messages in this recording.</p>
                  )}
                  {summary.pedals_truncated && (
                    <p>
                      Display limited to the first 2,000 controller events; the
                      original is complete.
                    </p>
                  )}
                </div>
                <div className="info-box">
                  <CircleHelp size={22} />
                  <p>
                    {summary.notice} Pedal values alone do not demonstrate
                    acoustic blurring. Activity-level alignment evidence,
                    optional audio and reports are available in session review.
                  </p>
                </div>
              </>
            ) : (
              <div className="empty-panel">
                <ChartNoAxesCombined size={36} />
                <h2>Start with a saved performance.</h2>
                <p>
                  Choose a session to view its velocity contour and original
                  damper values. Note accuracy requires a verified symbolic
                  score and alignment.
                </p>
              </div>
            )}
          </section>
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
              onClick={() => setModal("stop")}
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
        <div className="modal-backdrop">
          <div
            role="dialog"
            aria-modal="true"
            aria-label={
              modal === "shutdown"
                ? "Shut down Chopin Studio"
                : modal === "stop"
                  ? "Stop session"
                  : modal === "edit"
                    ? "Edit piece"
                    : "Settings and diagnostics"
            }
            className={`modal ${modal === "settings" ? "wide" : ""}`}
          >
            <div className="modal-heading">
              <h2>
                {modal === "shutdown"
                  ? "Shut down Chopin Studio?"
                  : modal === "stop"
                    ? "Finish this session?"
                    : modal === "edit"
                      ? "Your piece, your notes"
                      : "Settings & piano diagnostics"}
              </h2>
              <TouchButton
                className="icon-button"
                aria-label="Close dialog"
                disabled={busy}
                onClick={() => setModal(null)}
              >
                <X />
              </TouchButton>
            </div>
            {error && (
              <div className="banner error" role="alert">
                {error}
              </div>
            )}
            {modal === "shutdown" ? (
              <>
                <p>
                  Any active recording will be stopped and saved before the
                  backend shuts down. Flagged audio, including partial attempts, will then
                  be removed. Uncertain audio stays for review. Use
                  “Keep this audio” in Audio cleanup before shutting down to
                  protect recordings; MIDI is retained.
                </p>
                <p>
                  Closing this window normally leaves the backend and recording
                  running. Use the application icon to reopen it.
                </p>
                <div className="modal-actions">
                  <TouchButton
                    className="secondary"
                    disabled={busy}
                    onClick={() => setModal(null)}
                  >
                    Keep running
                  </TouchButton>
                  <TouchButton
                    className="stop-button"
                    disabled={busy}
                    onClick={() => void shutdown()}
                  >
                    <Power size={17} />
                    {busy ? "Saving & shutting down…" : "Save & shut down"}
                  </TouchButton>
                </div>
              </>
            ) : modal === "stop" ? (
              <>
                <p>
                  Your complete MIDI recording will be saved. You can keep
                  reading the score while the session finishes.
                </p>
                <div className="modal-actions">
                  <TouchButton
                    className="secondary"
                    onClick={() => setModal(null)}
                  >
                    Keep recording
                  </TouchButton>
                  <TouchButton
                    className="stop-button"
                    disabled={busy}
                    onClick={() => void stop()}
                  >
                    <Square size={17} />
                    {busy ? "Saving…" : "Stop & save session"}
                  </TouchButton>
                </div>
              </>
            ) : modal === "edit" && edit ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    await api(`/pieces/${edit.id}`, json("PUT", edit));
                    await refresh();
                    setModal(null);
                  });
                }}
              >
                <div className="form-grid">
                  {(["title", "genre", "opus", "musical_key"] as const).map(
                    (key) => (
                      <label key={key}>
                        {
                          {
                            title: "Title",
                            genre: "Genre",
                            opus: "Opus and number",
                            musical_key: "Key",
                          }[key]
                        }
                        <input
                          required={key === "title" || key === "genre"}
                          value={edit[key]}
                          onChange={(e) =>
                            setEdit({ ...edit, [key]: e.target.value })
                          }
                        />
                      </label>
                    ),
                  )}
                  <label>
                    PDF volume
                    <select
                      value={edit.volume_id}
                      onChange={(e) =>
                        setEdit({
                          ...edit,
                          volume_id: e.target.value,
                          start_page: null,
                          end_page: null,
                        })
                      }
                    >
                      {volumes.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Practice status
                    <select
                      value={edit.practice_status}
                      onChange={(e) =>
                        setEdit({
                          ...edit,
                          practice_status: e.target.value,
                          intent: e.target.value,
                        })
                      }
                    >
                      {[
                        "To explore",
                        "Learning",
                        "Maintaining",
                        "Resting",
                        "Review",
                        "Next",
                        "Planned",
                        "Dream",
                      ].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    First PDF page (1-based)
                    <input
                      type="number"
                      min="1"
                      value={edit.start_page || ""}
                      onChange={(e) =>
                        setEdit({
                          ...edit,
                          start_page: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    />
                  </label>
                  <label>
                    Last PDF page (inclusive)
                    <input
                      type="number"
                      min="1"
                      value={edit.end_page || ""}
                      onChange={(e) =>
                        setEdit({
                          ...edit,
                          end_page: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    />
                  </label>
                  <label>
                    Printed first page label
                    <input
                      value={edit.printed_page}
                      onChange={(e) =>
                        setEdit({ ...edit, printed_page: e.target.value })
                      }
                    />
                  </label>
                </div>
                <div className="form-grid">
                  <label>
                    Your learning level (1–3)
                    <input
                      type="number"
                      min="1"
                      max="3"
                      step=".5"
                      value={edit.mastery ?? ""}
                      onChange={(e) =>
                        setEdit({
                          ...edit,
                          mastery: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    />
                  </label>
                  <label>
                    Special liking (0–3 pluses)
                    <input
                      type="number"
                      min="0"
                      max="3"
                      value={edit.liking}
                      onChange={(e) =>
                        setEdit({ ...edit, liking: Number(e.target.value) })
                      }
                    />
                  </label>
                  <label>
                    Repertoire intention
                    <select
                      value={edit.intent}
                      onChange={(e) =>
                        setEdit({
                          ...edit,
                          intent: e.target.value,
                          practice_status: e.target.value,
                        })
                      }
                    >
                      {[
                        "Learning",
                        "Maintaining",
                        "Review",
                        "Next",
                        "Planned",
                        "Dream",
                        "To explore",
                      ].map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Preferred edition
                    <input
                      value={edit.preferred_edition}
                      onChange={(e) =>
                        setEdit({ ...edit, preferred_edition: e.target.value })
                      }
                    />
                  </label>
                  <label className="toggle-row">
                    Largely forgotten (X)
                    <input
                      type="checkbox"
                      checked={!!edit.forgotten}
                      onChange={(e) =>
                        setEdit({ ...edit, forgotten: e.target.checked })
                      }
                    />
                  </label>
                </div>
                <label>
                  Practice notes
                  <textarea
                    rows={3}
                    value={edit.notes}
                    onChange={(e) =>
                      setEdit({ ...edit, notes: e.target.value })
                    }
                  />
                </label>
                <p className="muted">
                  PDF page numbers are counted from 1, including cover pages.
                  Printed page labels are separate.
                </p>
                <TouchButton className="primary" disabled={busy}>
                  <Check size={18} />
                  Save piece
                </TouchButton>
              </form>
            ) : (
              <>
                <div className="settings-section">
                  <h3>
                    <Cable size={21} />
                    MIDI connection
                  </h3>
                  <label>
                    Preferred device name (stable portion)
                    <input
                      placeholder="e.g. CASIO or AP-470"
                      value={settings.preferred_device}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          preferred_device: e.target.value,
                        })
                      }
                    />
                  </label>
                  <p className="muted">
                    Casio devices connect automatically. Choose a detected
                    device to prefill its identity.
                  </p>
                  <div className="device-list">
                    {status?.devices.length ? (
                      status.devices.map((d) => (
                        <TouchButton
                          key={d}
                          className="secondary"
                          onClick={() =>
                            setSettings({
                              ...settings,
                              preferred_device: d.replace(/\s+\d+:\d+$/, ""),
                            })
                          }
                        >
                          {d}
                        </TouchButton>
                      ))
                    ) : (
                      <p>
                        No MIDI input detected. Connect the USB Type-B cable and
                        switch on the piano.
                      </p>
                    )}
                  </div>
                  {status?.device_error && (
                    <p className="warning-text">{status.device_error}</p>
                  )}
                  <TouchButton
                    className="secondary"
                    onClick={() =>
                      void run(() =>
                        api("/devices/reconnect", { method: "POST" }),
                      )
                    }
                  >
                    <RefreshCw size={18} />
                    Reconnect now
                  </TouchButton>
                  <div className="pedal-values">
                    {[64, 66, 67].map((cc, i) => (
                      <div key={cc}>
                        <span>
                          {["Damper", "Sostenuto", "Soft"][i]} · CC{cc}
                        </span>
                        <strong>
                          {status?.pedals[cc] || 0}
                          <small> / 127</small>
                        </strong>
                        <meter
                          min="0"
                          max="127"
                          value={status?.pedals[cc] || 0}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="diagnostics">
                    <span>
                      Held notes:{" "}
                      {Object.entries(status?.notes || {})
                        .map(([note, v]) => `${note.split(":")[1]} (v${v})`)
                        .join(", ") || "none"}
                    </span>
                    <span>
                      Rate: {status?.event_rate || 0} events/s · Queue:{" "}
                      {status?.queue_depth || 0} · Last input:{" "}
                      {status?.last_event_age == null
                        ? "none"
                        : status.last_event_age.toFixed(1) + " s ago"}
                    </span>
                  </div>
                  <details>
                    <summary>Recent MIDI messages</summary>
                    <div className="event-log">
                      {status?.recent
                        .slice()
                        .reverse()
                        .map((e, i) => (
                          <code key={i}>{e.message}</code>
                        ))}
                    </div>
                  </details>
                </div>
                <div className="settings-section">
                  <h3>
                    <SlidersHorizontal size={21} />
                    Touch & score controls
                  </h3>
                  {(
                    [
                      ["swipe", "Swipe to turn pages at fit scale"],
                      ["pinch", "Pinch to zoom; drag to pan when zoomed"],
                      [
                        "double_tap",
                        "Double tap to toggle fit / enlarged view",
                      ],
                      [
                        "tap_overlay",
                        "Single tap to show / hide practice controls",
                      ],
                      [
                        "auto_hide",
                        "Hide controls after 10 seconds of recording",
                      ],
                      ["pedal_enabled", "Enable pedal page turning"],
                    ] as const
                  ).map(([key, label]) => (
                    <label className="toggle-row" key={key}>
                      <span>{label}</span>
                      <input
                        type="checkbox"
                        checked={settings[key]}
                        onChange={(e) =>
                          setSettings({ ...settings, [key]: e.target.checked })
                        }
                      />
                    </label>
                  ))}
                  <label>
                    Page-turn pedal controller
                    <select
                      value={settings.pedal_controller ?? 66}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          pedal_controller: Number(e.target.value),
                        })
                      }
                    >
                      <option value={66}>Middle / sostenuto · CC66</option>
                      <option value={67}>Soft · CC67</option>
                      <option value={64}>Damper pedal (CC64)</option>
                    </select>
                  </label>
                  <label>
                    Piece separation cooldown (seconds)
                    <input
                      type="number"
                      min={5}
                      max={300}
                      value={settings.separation_cooldown ?? 20}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          separation_cooldown: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <div className="info-box">
                    <CircleHelp size={20} />
                    <p>
                      Pedal page control is disabled by default. Select the
                      controller that moves in the device readout. The selected
                      pedal's musical function still sounds on the piano. is the
                      usual middle pedal. Test: single press → next, double
                      press → previous, hold over 0.8 s → controls. This does
                      not disable the piano’s internal sostenuto. Raw pedal data
                      is always recorded; command interpretation is tagged in
                      the journal. Keyboard arrows or an external USB pedal are
                      alternatives.
                    </p>
                  </div>
                </div>
                <div className="settings-section">
                  <h3>
                    <Piano size={21} />
                    Simulation & installation check
                  </h3>
                  <p>
                    Feed a synthetic scale or saved MIDI through the same
                    recorder input. Simulated performances are marked in the
                    journal. No hardware validation is implied.
                  </p>
                  <div className="button-row">
                    <TouchButton
                      className="secondary"
                      disabled={busy}
                      onClick={() =>
                        void run(() =>
                          api(
                            status?.simulation
                              ? "/simulation/stop"
                              : "/simulation/start",
                            status?.simulation
                              ? { method: "POST" }
                              : json("POST", {}),
                          ),
                        )
                      }
                    >
                      {status?.simulation
                        ? "Stop simulation"
                        : "Play synthetic scale"}
                    </TouchButton>
                    <TouchButton
                      className="secondary"
                      onClick={() => midiImport.current?.click()}
                    >
                      <Upload size={18} />
                      Import MIDI / CSV
                    </TouchButton>
                  </div>
                  <select
                    aria-label="Replay imported session"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value)
                        void run(() =>
                          api(
                            "/simulation/start",
                            json("POST", {
                              session_id: e.target.value,
                              speed: 1,
                            }),
                          ),
                        );
                      e.target.value = "";
                    }}
                  >
                    <option value="">Replay a saved recording as input…</option>
                    {sessions
                      .filter((s) => s.status !== "recording")
                      .map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                  </select>
                  <p className="muted">
                    Simulation produces MIDI input, not sound. Request optional
                    audio rendering from a saved activity in session review.
                  </p>
                </div>
                <div className="modal-actions">
                  <TouchButton
                    className="primary"
                    disabled={busy}
                    onClick={() => void saveSettings()}
                  >
                    <Check size={18} />
                    Save settings
                  </TouchButton>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {busy && (
        <div className="busy-indicator" role="status">
          Working…
        </div>
      )}
    </div>
  );
}
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
function SessionDetail({
  session,
  summary,
  onAnalysis,
  onDelete,
}: {
  session: Session;
  summary: any;
  onAnalysis: () => void;
  onDelete: React.ReactNode;
}) {
  return (
    <>
      <div className="detail-heading">
        <h2>{session.name.replaceAll("_", " ")}</h2>
        <p>
          {new Date(session.started).toLocaleString()} · {session.status}
        </p>
      </div>
      {session.error && (
        <div className="info-box warning-text">{session.error}</div>
      )}
      <div className="metric-grid">
        <Metric label="Recording length" value={clock(session.duration)} />
        <Metric label="MIDI events" value={session.events.toLocaleString()} />
        <Metric
          label="Note onsets"
          value={summary ? summary.notes.toLocaleString() : "…"}
        />
      </div>
      <div className="button-row">
        <a
          className="button primary"
          href={`/api/sessions/${session.id}/midi`}
          download
        >
          <Download size={19} />
          Export original MIDI
        </a>
        <TouchButton className="secondary" onClick={onAnalysis}>
          <ChartNoAxesCombined size={19} />
          View MIDI measurements
        </TouchButton>
        {onDelete}
      </div>
      {summary?.markers.length > 0 && (
        <div className="chart-panel">
          <h3>Connection & session markers</h3>
          {summary.markers.map((m: any, i: number) => (
            <p key={i}>
              {clock(m.t)} · {m.kind.replaceAll("_", " ")}
            </p>
          ))}
        </div>
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
