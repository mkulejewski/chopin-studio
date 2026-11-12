import { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { TouchButton as Button } from "./TouchButton";
import { startReasonDictation } from "./reasonDictation";
import type { SpeechWindow } from "./speechRecognition";

export function ReasonDictation({
  disabled,
  onText,
  onActiveChange,
}: {
  disabled: boolean;
  onText: (text: string) => void;
  onActiveChange: (active: boolean) => void;
}) {
  const [active, setActive] = useState(false);
  const [status, setStatus] = useState("");
  const session = useRef<ReturnType<typeof startReasonDictation> | null>(null);
  const callbacks = useRef({ onText, onActiveChange });
  callbacks.current = { onText, onActiveChange };
  useEffect(
    () => () => {
      session.current?.cancel();
    },
    [],
  );
  function start() {
    const speech = window as SpeechWindow;
    const Constructor =
      speech.SpeechRecognition || speech.webkitSpeechRecognition;
    if (!Constructor) {
      setStatus(
        "Speech recognition is unavailable in this browser. You can still type the reason.",
      );
      return;
    }
    setActive(true);
    callbacks.current.onActiveChange(true);
    session.current = startReasonDictation(Constructor, {
      onText: (text) => callbacks.current.onText(text),
      onStatus: setStatus,
      onEnd: () => {
        setActive(false);
        callbacks.current.onActiveChange(false);
      },
    });
  }
  return (
    <div className="reason-dictation">
      <div className="learning-controls">
        <Button
          type="button"
          disabled={disabled}
          onClick={() => (active ? session.current?.stop() : start())}
        >
          {active ? <Square size={16} /> : <Mic size={16} />}
          {active ? "Stop dictation" : "Dictate reason"}
        </Button>
        {active && (
          <Button type="button" onClick={() => session.current?.cancel()}>
            Cancel dictation
          </Button>
        )}
      </div>
      <small>
        Uses your browser’s speech recognition; audio may be processed by its
        speech service.
      </small>
      {status && <p role="status">{status}</p>}
    </div>
  );
}
