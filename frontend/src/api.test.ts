import { describe, it, expect, vi, afterEach } from "vitest";
import { api, clock, json } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("practice time formatting", () => {
  it("keeps multi-hour sessions continuous", () => {
    expect(clock(0)).toBe("00:00");
    expect(clock(3601.8)).toBe("60:01");
  });
});
describe("local API", () => {
  it("surfaces backend errors instead of reporting a successful save", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Bad request",
        json: async () => ({ detail: "Disk full" }),
      }),
    );
    await expect(api("/record/stop")).rejects.toThrow("Disk full");
  });
  it("serialises settings without dropping false values", () => {
    expect(
      JSON.parse(json("PUT", { pedal_enabled: false }).body as string),
    ).toEqual({ pedal_enabled: false });
  });
});
