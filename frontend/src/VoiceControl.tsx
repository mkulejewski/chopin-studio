import { useEffect, useRef, useState } from "react";
import { Mic, Square, X } from "lucide-react";
import { TouchButton } from "./TouchButton";

import type { Recognition, SpeechWindow } from "./speechRecognition";

export function VoiceControl({
  onCommand,
}: {
  onCommand: (text: string) => string;
}) {
  const [listening, setListening] = useState(false);
  const [message, setMessage] = useState("");
  const current = useRef<Recognition | null>(null);
  const callback = useRef(onCommand);
  callback.current = onCommand;
  const cleanup = useRef<() => void>(() => {});
  useEffect(() => () => cleanup.current(), []);
  const speechWindow = window as SpeechWindow;
  const Constructor =
    speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;

  function start() {
    if (current.current) {
      cleanup.current();
      setListening(false);
      setMessage("Voice command cancelled.");
      return;
    }
    if (!Constructor) {
      setMessage(
        "Voice control is unavailable in this browser. Try Chrome or Safari with microphone access.",
      );
      return;
    }
    const recognition = new Constructor();
    let finalText = "";
    let failed = false;
    let stopping = false;
    let pauseTimer: ReturnType<typeof setTimeout> | undefined;
    let endTimer: ReturnType<typeof setTimeout> | undefined;
    let limitTimer: ReturnType<typeof setTimeout> | undefined;
    function clearTimers() {
      clearTimeout(pauseTimer);
      clearTimeout(endTimer);
      clearTimeout(limitTimer);
    }
    const dispose = () => {
      clearTimers();
      recognition.onend = recognition.onresult = recognition.onerror = null;
      recognition.onspeechstart = recognition.onspeechend = null;
      current.current = null;
      recognition.abort();
    };
    cleanup.current = dispose;
    const finish = () => {
      if (current.current !== recognition) return;
      dispose();
      setListening(false);
      if (!failed)
        setMessage(
          finalText
            ? callback.current(finalText)
            : "No speech recognised. Tap the microphone to try again.",
        );
    };
    function stop() {
      if (stopping || current.current !== recognition) return;
      stopping = true;
      clearTimers();
      setMessage("Finishing voice command…");
      endTimer = setTimeout(finish, 4000);
      try {
        recognition.stop();
      } catch {
        finish();
      }
    }
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      const results = Array.from(event.results);
      finalText = results
        .filter((result) => result.isFinal)
        .map((result) => result[0].transcript)
        .join(" ")
        .trim();
      const heard = results
        .map((result) => result[0].transcript)
        .join(" ")
        .trim();
      setMessage(heard ? `Heard: “${heard}”` : "Listening…");
    };
    recognition.onspeechend = () => {
      clearTimeout(pauseTimer);
      pauseTimer = setTimeout(stop, 800);
    };
    recognition.onspeechstart = () => {
      clearTimeout(pauseTimer);
    };
    recognition.onerror = ({ error }) => {
      failed = true;
      setMessage(
        error === "not-allowed" || error === "service-not-allowed"
          ? "Microphone or speech recognition permission was denied. Allow access in your browser and try again."
          : error === "audio-capture"
            ? "No microphone is available. Connect one and try again."
            : error === "network"
              ? "Speech recognition could not connect. Check your connection and try again."
              : error === "no-speech"
                ? "No speech recognised. Tap the microphone to try again."
                : `Voice recognition stopped (${error}). Tap to try again.`,
      );
      finish();
    };
    recognition.onend = finish;
    current.current = recognition;
    setListening(true);
    setMessage(
      "Listening… Say “Open Nocturne Opus Nine Number One”. Tap again to cancel.",
    );
    limitTimer = setTimeout(stop, 20000);
    try {
      recognition.start();
    } catch {
      failed = true;
      setMessage(
        "Could not start voice recognition. Check microphone permission and use HTTPS or localhost.",
      );
      finish();
    }
  }
  return (
    <div className="voice-control">
      <TouchButton
        className={`voice-button ${listening ? "listening" : ""}`}
        type="button"
        aria-label={listening ? "Cancel voice command" : "Voice command"}
        aria-pressed={listening}
        aria-describedby={message ? "voice-feedback" : undefined}
        onClick={start}
        title="Open a piece by voice"
      >
        {listening ? <Square size={18} /> : <Mic size={19} />}
        <span>{listening ? "Listening…" : "Voice"}</span>
      </TouchButton>
      {message && (
        <div className="voice-feedback" id="voice-feedback" role="status">
          <span>{message}</span>
          {!listening && (
            <TouchButton
              type="button"
              className="icon-button"
              aria-label="Dismiss voice feedback"
              onClick={() => setMessage("")}
            >
              <X size={16} />
            </TouchButton>
          )}
        </div>
      )}
    </div>
  );
}
