import { describe, expect, it } from "vitest";
import { resolveVoiceCommand } from "./voiceCommands";
import type { Piece } from "./api";
const pieces = [
  {
    id: "n9-1",
    title: "Nocturne",
    genre: "Nocturnes",
    opus: "9 · No. 1",
    musical_key: "B-flat minor",
  },
  {
    id: "n9-2",
    title: "Nocturne",
    genre: "Nocturnes",
    opus: "9 · No. 2",
    musical_key: "E-flat major",
  },
  {
    id: "n27-2",
    title: "Nocturne",
    genre: "Nocturnes",
    opus: "27 · No. 2",
    musical_key: "D-flat major",
  },
] as Piece[];
describe("voice commands", () => {
  it.each([
    ["open Nocturne Opus Nine Number One", "n9-1"],
    ["Please open Nocturne Op. 9 No. 2.", "n9-2"],
    ["Show Nocturne opus twenty-seven number two", "n27-2"],
    ["load the nocturne in B flat minor", "n9-1"],
  ])("resolves %s", (command, id) => {
    expect(resolveVoiceCommand(command, pieces).piece?.id).toBe(id);
  });
  it("does not guess ambiguous or unknown pieces", () => {
    expect(resolveVoiceCommand("open nocturne", pieces).message).toContain(
      "3 pieces",
    );
    expect(
      resolveVoiceCommand("open nocturne opus 99 number 1", pieces).piece,
    ).toBeUndefined();
    expect(
      resolveVoiceCommand("open nocturne opus 9 number 11", pieces).piece,
    ).toBeUndefined();
  });
  it("keeps opus and piece numbers distinct", () => {
    const collision = { ...pieces[0], id: "other", opus: "1 · No. 9" };
    const library = [...pieces, collision];
    expect(
      resolveVoiceCommand("open nocturne opus nine number one", library).piece
        ?.id,
    ).toBe("n9-1");
    expect(
      resolveVoiceCommand("open nocturne number nine", library).piece?.id,
    ).toBe("other");
    expect(
      resolveVoiceCommand("open nocturne opus nine number nine", library).piece,
    ).toBeUndefined();
  });
  it("requires a supported command", () => {
    expect(
      resolveVoiceCommand("delete nocturne", pieces).piece,
    ).toBeUndefined();
    expect(resolveVoiceCommand("open the", pieces).piece).toBeUndefined();
  });
});
