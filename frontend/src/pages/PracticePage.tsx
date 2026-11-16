import {
  BookOpen,
  Circle,
  Eye,
  Music2,
  SlidersHorizontal,
  Square,
  Volume2,
} from "lucide-react";
import React from "react";
import { LivePanel } from "../LivePanel";
import { Score } from "../Score";
import { TouchButton } from "../TouchButton";
import { clock, type Piece, type Settings, type Volume } from "../api";
import type { Status } from "../appTypes";

type Props = {
  piece: Piece | null;
  setTab: (next: string) => void;
  hidden: boolean;
  scoreFullscreenHost: HTMLElement | null;
  pieces: Piece[];
  settings: Settings;
  setSettings: React.Dispatch<React.SetStateAction<Settings>>;
  choose: (p: Piece) => void;
  setAutomaticCommand: React.Dispatch<
    React.SetStateAction<{
      id: number;
      action: string;
      page?: number;
      piece_id?: string;
    } | null>
  >;
  fail: (e: unknown) => void;
  status: Status | null;
  recordMidi: boolean;
  busy: boolean;
  setRecordMidi: React.Dispatch<React.SetStateAction<boolean>>;
  recordMicrophone: boolean;
  setRecordMicrophone: React.Dispatch<React.SetStateAction<boolean>>;
  microphoneDevice: string;
  setMicrophoneDevice: React.Dispatch<React.SetStateAction<string>>;
  record: (microphoneOverride?: boolean) => Promise<void>;
  changeAutoTurns: (enabled: boolean) => Promise<void>;
  setScoreFullscreenHost: React.Dispatch<
    React.SetStateAction<HTMLElement | null>
  >;
  setModal: React.Dispatch<
    React.SetStateAction<"settings" | "stop" | "edit" | "shutdown" | null>
  >;
  clearScore: () => void;
  automaticCommand: {
    id: number;
    action: string;
    page?: number;
    piece_id?: string;
  } | null;
  volume: Volume | undefined;
  command: {
    actions?: { action: string }[];
    id: number;
    action: string;
    page?: number;
    piece_id?: string;
  } | null;
  setHidden: React.Dispatch<React.SetStateAction<boolean>>;
};

export function PracticePage({
  piece,
  setTab,
  hidden,
  scoreFullscreenHost,
  pieces,
  settings,
  setSettings,
  choose,
  setAutomaticCommand,
  fail,
  status,
  recordMidi,
  busy,
  setRecordMidi,
  recordMicrophone,
  setRecordMicrophone,
  microphoneDevice,
  setMicrophoneDevice,
  record,
  changeAutoTurns,
  setScoreFullscreenHost,
  setModal,
  clearScore,
  automaticCommand,
  volume,
  command,
  setHidden,
}: Props) {
  return (
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
          <TouchButton className="secondary" onClick={() => setTab("Library")}>
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
              checked={status?.active ? !!status.midi_enabled : recordMidi}
              disabled={!!status?.active || busy}
              onChange={(e) => setRecordMidi(e.target.checked)}
            />
          </label>
          <label className="toggle-row">
            Record laptop microphone
            <input
              type="checkbox"
              checked={
                status?.active ? !!status.microphone_enabled : recordMicrophone
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
              {recordMidi ? "Record microphone + MIDI" : "Record microphone"}
            </TouchButton>
          )}
          <p className="muted">
            Choose sources before starting. Microphone uses the laptop’s system
            input and saves lossless mono audio locally. Select the built-in
            microphone in system sound settings. About 5.76 MB/min before FLAC
            compression. With microphone on, unplugging MIDI does not stop the
            session.
          </p>
        </div>
        <Score
          onAutoTurnChange={changeAutoTurns}
          onFullscreenHost={setScoreFullscreenHost}
          fullscreenControls={
            <div className="tool-group" aria-label="Session recording">
              <span className="timer" aria-live="off">
                {clock(status?.duration || 0)}
              </span>
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
            </div>
          }
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
            <span className={status?.active ? "record-dot" : "ready-dot"} />
            <div>
              <strong>
                {status?.active ? "Session recording" : "Ready when you are"}
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
  );
}
