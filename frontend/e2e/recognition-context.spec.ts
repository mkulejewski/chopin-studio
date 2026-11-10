import { test, expect } from "@playwright/test";

test("unrecognised live notes fall back to the open score without a page request", async ({
  page,
}) => {
  const previous = await (await page.request.get("/api/settings")).json();
  await page.request.put("/api/settings", {
    data: {
      ...previous,
      live_enabled: true,
      live_auto_turn: true,
      live_piece_id: null,
    },
  });
  const csv =
    "0, 0, Header, 0, 1, 480\n1, 0, Start_track\n1, 0, Tempo, 500000\n1, 0, Note_on_c, 0, 100, 80\n1, 240, Note_off_c, 0, 100, 0\n1, 480, Note_on_c, 0, 102, 80\n1, 720, Note_off_c, 0, 102, 0\n1, 960, Note_on_c, 0, 104, 80\n1, 1200, Note_off_c, 0, 104, 0\n1, 1920, End_track\n0, 0, End_of_file\n";
  const imported = await page.request.post("/api/import/midi", {
    multipart: {
      file: {
        name: "context-notes.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(csv),
      },
    },
  });
  expect(imported.ok()).toBeTruthy();
  const { id } = await imported.json();
  await page.addInitScript(() => localStorage.setItem("chopin-piece", "n72-1"));
  const context = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/live/context") &&
      request.method() === "PUT" &&
      request.postDataJSON()?.piece_id === "n72-1",
  );
  try {
    await page.goto("/");
    expect((await context).postDataJSON()).toEqual({ piece_id: "n72-1" });
    expect(
      (
        await page.request.post("/api/simulation/start", {
          data: { session_id: id, speed: 1 },
        })
      ).ok(),
    ).toBeTruthy();
    await expect(page.locator(".live-summary")).toContainText(
      "assuming open score (unconfirmed)",
    );
    const live = await (await page.request.get("/api/live")).json();
    expect(live.piece_id).toBe("n72-1");
    expect(live.assumed).toBe(true);
    expect(live.measure).toBeNull();
    expect(live.page_request).toBeUndefined();
  } finally {
    await page.request.post("/api/simulation/stop");
    await page.request.put("/api/settings", { data: previous });
  }
});
