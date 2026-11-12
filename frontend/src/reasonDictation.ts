import type { Recognition } from "./speechRecognition";

/** One bounded dictation session. Only final results replace the saved reason. */
export function startReasonDictation(
  Constructor: new () => Recognition,
  callbacks: {
    onText: (text: string) => void;
    onStatus: (text: string) => void;
    onEnd: () => void;
  },
) {
  const recognition = new Constructor();
  let ended = false;
  let failed = false;
  let stopping = false;
  let finalText = "";
  let stopTimer: ReturnType<typeof setTimeout> | undefined;
  let limitTimer: ReturnType<typeof setTimeout> | undefined;
  const finish = () => {
    if (ended) return;
    ended = true;
    clearTimeout(stopTimer);
    clearTimeout(limitTimer);
    recognition.onresult = recognition.onerror = recognition.onend = null;
    try {
      recognition.abort();
    } catch {
      /* Already stopped. */
    }
    if (!failed) {
      if (finalText) {
        callbacks.onText(finalText.slice(0, 1000));
        callbacks.onStatus(
          "Reason transcribed. Review or edit it before saving.",
        );
      } else {
        callbacks.onStatus(
          "No speech recognised. Your reason has been kept; try again or type it.",
        );
      }
    }
    callbacks.onEnd();
  };
  const stop = () => {
    if (ended || stopping) return;
    stopping = true;
    callbacks.onStatus("Finishing dictation…");
    stopTimer = setTimeout(finish, 4000);
    try {
      recognition.stop();
    } catch {
      finish();
    }
  };
  const cancel = () => {
    if (ended) return;
    failed = true;
    callbacks.onStatus("Dictation cancelled. Your reason has been kept.");
    finish();
  };
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.onresult = ({ results }) => {
    if (ended) return;
    const entries = Array.from(results);
    finalText = entries
      .filter((r) => r.isFinal)
      .map((r) => r[0].transcript)
      .join(" ")
      .trim();
    const heard = entries
      .map((r) => r[0].transcript)
      .join(" ")
      .trim();
    callbacks.onStatus(heard ? `Heard: “${heard}”` : "Listening…");
  };
  recognition.onerror = ({ error }) => {
    failed = true;
    callbacks.onStatus(
      error === "not-allowed" || error === "service-not-allowed"
        ? "Microphone or speech recognition permission was denied. You can still type the reason."
        : error === "network"
          ? "Speech recognition could not connect. Try again or type the reason."
          : error === "audio-capture"
            ? "No microphone is available. You can still type the reason."
            : "No speech could be transcribed. Try again or type the reason.",
    );
    finish();
  };
  recognition.onend = finish;
  callbacks.onStatus(
    "Listening… Speak your reason, then press Stop dictation.",
  );
  limitTimer = setTimeout(stop, 45000);
  try {
    recognition.start();
  } catch {
    failed = true;
    callbacks.onStatus(
      "Could not start speech recognition. You can still type the reason.",
    );
    finish();
  }
  return { stop, cancel };
}
