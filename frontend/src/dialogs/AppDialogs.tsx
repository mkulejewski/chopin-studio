import { Power, Square, X } from "lucide-react";
import React from "react";
import { TouchButton } from "../TouchButton";
import { type Piece, type Session, type Settings, type Volume } from "../api";
import type { Status } from "../appTypes";
import { ModalBackdrop } from "../components/AppPrimitives";
import { PieceEditor } from "./PieceEditor";
import { SettingsDialog } from "./SettingsDialog";

type Props = {
  scoreFullscreenHost: HTMLElement | null;
  modal: "settings" | "stop" | "edit" | "shutdown";
  busy: boolean;
  setModal: React.Dispatch<
    React.SetStateAction<"settings" | "stop" | "edit" | "shutdown" | null>
  >;
  error: string;
  shutdown: () => Promise<void>;
  stop: () => Promise<void>;
  edit: Piece | null;
  run: (action: () => Promise<unknown>) => Promise<void>;
  refresh: () => Promise<void>;
  setEdit: React.Dispatch<React.SetStateAction<Piece | null>>;
  volumes: Volume[];
  settings: Settings;
  setSettings: React.Dispatch<React.SetStateAction<Settings>>;
  status: Status | null;
  midiImport: React.RefObject<HTMLInputElement | null>;
  sessions: Session[];
  saveSettings: () => Promise<void>;
};

export function AppDialogs({
  scoreFullscreenHost,
  modal,
  busy,
  setModal,
  error,
  shutdown,
  stop,
  edit,
  run,
  refresh,
  setEdit,
  volumes,
  settings,
  setSettings,
  status,
  midiImport,
  sessions,
  saveSettings,
}: Props) {
  return (
    <ModalBackdrop host={scoreFullscreenHost}>
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
              Any active recording will be stopped and saved before the backend
              shuts down. Flagged audio, including partial attempts, will then
              be removed. Uncertain audio stays for review. Use “Keep this
              audio” in Audio cleanup before shutting down to protect
              recordings; MIDI is retained.
            </p>
            <p>
              The dedicated app window closes after shutdown finishes. Closing
              the window normally leaves the backend and recording running. Use
              the application icon to reopen it.
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
              Your complete MIDI recording will be saved. You can keep reading
              the score while the session finishes.
            </p>
            <div className="modal-actions">
              <TouchButton className="secondary" onClick={() => setModal(null)}>
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
          <PieceEditor
            run={run}
            edit={edit}
            refresh={refresh}
            setModal={setModal}
            setEdit={setEdit}
            volumes={volumes}
            busy={busy}
          />
        ) : (
          <SettingsDialog
            settings={settings}
            setSettings={setSettings}
            status={status}
            run={run}
            busy={busy}
            midiImport={midiImport}
            sessions={sessions}
            saveSettings={saveSettings}
          />
        )}
      </div>
    </ModalBackdrop>
  );
}
