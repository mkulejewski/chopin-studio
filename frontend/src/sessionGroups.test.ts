import { describe, expect, it } from "vitest";
import { sessionEntries } from "./sessionGroups";
import type { Session } from "./api";
const session = (
  id: string,
  started: string,
  changes: Partial<Session> = {},
): Session => ({
  id,
  started,
  name: `Take ${id}`,
  source: "learning",
  duration: 6,
  events: 10,
  status: "saved",
  error: null,
  learning_piece_id: "e25-1",
  learning_piece_title: "Étude “Aeolian Harp”",
  learning_piece_opus: "25 · No. 1",
  ...changes,
});
describe("daily Learning session groups", () => {
  it("combines all takes for a piece/local day while preserving originals and sorting by newest take", () => {
    const takes = [
      session("first", "2026-11-10T23:30:00Z"),
      session("second", "2026-11-11T10:00:00Z"),
      session("practice", "2026-11-11T11:00:00Z", {
        source: "live",
        learning_piece_id: null,
      }),
      session("other-piece", "2026-11-11T08:00:00Z", {
        learning_piece_id: "n9-1",
        learning_piece_title: "Nocturne",
      }),
    ];
    const before = JSON.stringify(takes);
    const rows = sessionEntries(takes, "Europe/Warsaw");
    expect(rows).toHaveLength(3);
    expect(rows[0].kind).toBe("session");
    const group = rows[1];
    expect(group.kind).toBe("learning");
    if (group.kind !== "learning") throw new Error("Expected daily group");
    expect(group.day).toBe("2026-11-11");
    expect(group.takes.map((t) => t.id)).toEqual(["second", "first"]);
    expect(group.duration).toBe(12);
    expect(group.events).toBe(20);
    expect(group.title).toBe("Learning Étude “Aeolian Harp” Session");
    expect(JSON.stringify(takes)).toBe(before);
  });
  it("separates local dates, including late-night UTC recordings", () => {
    const rows = sessionEntries(
      [
        session("a", "2026-11-11T22:59:00Z"),
        session("b", "2026-11-11T23:01:00Z"),
      ],
      "Europe/Warsaw",
    );
    expect(rows.map((row) => (row.kind === "learning" ? row.day : ""))).toEqual(
      ["2026-11-12", "2026-11-11"],
    );
  });
  it("handles the repeated hour at a daylight-saving transition", () => {
    const rows = sessionEntries(
      [
        session("a", "2026-10-25T00:30:00Z"),
        session("b", "2026-10-25T01:30:00Z"),
      ],
      "Europe/Warsaw",
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].kind === "learning" && rows[0].takes.length).toBe(2);
  });
  it("does not infer a piece from a session name or group an unattributed session", () => {
    expect(
      sessionEntries(
        [
          session("a", "2026-11-11T10:00:00Z", { learning_piece_id: null }),
          session("b", "2026-11-11T11:00:00Z", { started: "invalid date" }),
        ],
        "Europe/Warsaw",
      ).every((row) => row.kind === "session"),
    ).toBe(true);
  });
});
