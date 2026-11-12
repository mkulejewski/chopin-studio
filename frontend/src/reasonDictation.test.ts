import { afterEach, describe, expect, it, vi } from "vitest";
import { startReasonDictation } from "./reasonDictation";
import type { Recognition } from "./speechRecognition";

class FakeRecognition implements Recognition {
  static latest: FakeRecognition;
  lang = "";
  continuous = true;
  interimResults = false;
  onresult: Recognition["onresult"] = null;
  onerror: Recognition["onerror"] = null;
  onend: Recognition["onend"] = null;
  onspeechend: Recognition["onspeechend"] = null;
  onspeechstart: Recognition["onspeechstart"] = null;
  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();
  constructor() {
    FakeRecognition.latest = this;
  }
}
function setup() {
  const callbacks = { onText: vi.fn(), onStatus: vi.fn(), onEnd: vi.fn() };
  const session = startReasonDictation(FakeRecognition, callbacks);
  return { ...callbacks, ...session, speech: FakeRecognition.latest };
}
const result = (text: string, isFinal = true) => ({
  results: [{ isFinal, 0: { transcript: text } }],
});
afterEach(() => vi.useRealTimers());

describe("reason dictation", () => {
  it("waits for final recognition after Stop and commits editable text once", () => {
    const s = setup();
    s.speech.onresult!(result("The score has a flat here", false));
    expect(s.onText).not.toHaveBeenCalled();
    s.stop();
    expect(s.speech.stop).toHaveBeenCalledOnce();
    s.speech.onresult!(result("The score has a flat here."));
    s.speech.onend!();
    expect(s.onText).toHaveBeenCalledExactlyOnceWith(
      "The score has a flat here.",
    );
    expect(s.speech.abort).toHaveBeenCalledOnce();
    expect(s.speech.onresult).toBeNull();
    expect(s.onEnd).toHaveBeenCalledOnce();
  });
  it("cancels without replacing the original reason or accepting late results", () => {
    const s = setup();
    s.speech.onresult!(result("discard this"));
    const late = s.speech.onresult!;
    s.cancel();
    late(result("late result"));
    expect(s.onText).not.toHaveBeenCalled();
    expect(s.onEnd).toHaveBeenCalledOnce();
    expect(s.speech.abort).toHaveBeenCalledOnce();
  });
  it("keeps the existing reason when permission or network recognition fails", () => {
    for (const error of ["not-allowed", "network", "audio-capture"]) {
      const s = setup();
      s.speech.onerror!({ error });
      expect(s.onText).not.toHaveBeenCalled();
      expect(s.speech.abort).toHaveBeenCalledOnce();
      expect(s.onEnd).toHaveBeenCalledOnce();
    }
  });
  it("keeps the existing reason if only an interim result was heard", () => {
    const s = setup();
    s.speech.onresult!(result("unfinished", false));
    s.speech.onend!();
    expect(s.onText).not.toHaveBeenCalled();
    expect(s.onStatus).toHaveBeenLastCalledWith(
      expect.stringContaining("No speech recognised"),
    );
  });
  it("bounds recording and releases the microphone if the browser never ends", () => {
    vi.useFakeTimers();
    const s = setup();
    s.speech.onresult!(result("x".repeat(1100)));
    vi.advanceTimersByTime(45000);
    expect(s.speech.stop).toHaveBeenCalledOnce();
    vi.advanceTimersByTime(4000);
    expect(s.speech.abort).toHaveBeenCalledOnce();
    expect(s.onText).toHaveBeenCalledExactlyOnceWith("x".repeat(1000));
    expect(s.onEnd).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });
});
