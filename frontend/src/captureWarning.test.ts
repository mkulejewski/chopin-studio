import { describe, expect, it } from "vitest";
import { captureWarning } from "./captureWarning";

const historical =
  "Microphone stopped unexpectedly or reported capture errors: arecord: pcm_read:2240: read error: Interrupted system call";
describe("saved capture warnings", () => {
  it("hides only the obsolete clean-stop diagnostic, including signal shutdown lines", () => {
    expect(captureWarning(historical)).toBeNull();
    expect(
      captureWarning(historical + "\nAborted by signal Interrupt..."),
    ).toBeNull();
    expect(captureWarning(null)).toBeNull();
  });
  it("keeps real audio errors even when the stop diagnostic is also present", () => {
    for (const error of [
      "overrun!!!",
      "Microphone save failed: disk full",
      "Microphone capture ended early.",
      historical + "\noverrun!!!",
    ]) {
      expect(captureWarning(error)).toBe(error);
    }
  });
  it("retains independent storage and MIDI errors alongside the old microphone notice", () => {
    expect(captureWarning("MIDI journal overflow; " + historical)).toBe(
      "MIDI journal overflow",
    );
    expect(captureWarning(historical + "; Storage write failed")).toBe(
      "Storage write failed",
    );
  });
});
