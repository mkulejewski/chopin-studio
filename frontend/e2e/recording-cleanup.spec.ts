import { test, expect } from "@playwright/test";

test("an accidental empty session can be deleted from the session list", async ({
  page,
}) => {
  const session = {
    id: "accidental-nine-seconds",
    name: "Accidental empty session",
    started: "2026-11-09T10:00:00Z",
    duration: 9,
    events: 0,
    status: "saved",
    error: null,
  };
  let sessions = [session];
  const deleted: unknown[] = [];
  await page.route("**/api/sessions", (route) =>
    route.fulfill({ json: sessions }),
  );
  await page.route(`**/api/sessions/${session.id}`, (route) => {
    expect(route.request().method()).toBe("DELETE");
    deleted.push(route.request().postDataJSON());
    sessions = [];
    return route.fulfill({ json: { ok: true } });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Recording sources" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Record microphone + MIDI", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await page.getByRole("button", { name: "Delete session", exact: true }).tap();
  const dialog = page.getByRole("alertdialog", {
    name: "Delete this session?",
  });
  await expect(dialog).toContainText("00:09");
  await dialog.getByRole("button", { name: "Cancel", exact: true }).tap();
  expect(deleted).toEqual([]);
  await page.getByRole("button", { name: "Delete session", exact: true }).tap();
  await dialog.screenshot({
    path: `/tmp/chopin-delete-session-${test.info().project.name}.png`,
  });
  await dialog
    .getByRole("button", { name: "Delete permanently", exact: true })
    .tap();
  await expect(
    page.getByText("Your first session starts at the piano."),
  ).toBeVisible();
  expect(deleted).toEqual([{ confirmation: "delete" }]);
});

test("audio cleanup keeps MIDI and confirms only audio removal", async ({
  page,
}) => {
  const session = {
    id: "cleanup-session",
    name: "Cleanup session",
    started: "2026-11-09T10:00:00Z",
    duration: 300,
    events: 100,
    status: "saved",
    error: null,
    bytes: 10000000,
    audio_bytes: 9000000,
  };
  let takes = Array.from({ length: 4 }, (_, i) => ({
    id: `take-${i}`,
    session_id: session.id,
    title: "Nocturne",
    opus: "9 · No. 1",
    piece_id: "n9-1",
    start: i * 60,
    end: (i + 1) * 60,
    started: session.started,
    revision: 1,
    eligible: i !== 3,
    complete: i !== 3,
    choice: "auto",
    action: i < 2 ? "keep" : "remove",
    reason: i < 2 ? "One of the best two takes." : "Flagged for removal.",
    eligibility_reason: i === 3 ? "Partial or uncertain." : "Complete.",
    ranking_notice: "Listen before deleting.",
    pitch_score: i === 3 ? null : 98 - i,
    quality_score: i === 3 ? null : 98 - i,
    quality_ranking: {
      components: { notes: 98 - i, timing: 95, dynamics: 90 },
    },
  }));
  const requests: unknown[] = [];
  await page.route("**/api/sessions", (route) =>
    route.fulfill({ json: [session] }),
  );
  await page.route("**/api/recordings", (route) =>
    route.fulfill({
      json: { takes, sessions: [session], policy: "two takes" },
    }),
  );
  await page.route("**/api/recordings/take-*/audio", (route) => {
    requests.push({
      method: route.request().method(),
      body: route.request().postDataJSON(),
    });
    const id = route.request().url().split("/").at(-2);
    if (route.request().method() === "DELETE")
      takes = takes.filter((t) => t.id !== id);
    return route.fulfill({ json: { ok: true } });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await page
    .getByRole("button", {
      name: "Audio cleanup · kept & flagged recordings",
      exact: true,
    })
    .tap();
  const cleanup = page.getByRole("region", { name: "Audio cleanup" });
  await page.getByRole("button", { name: "Practice", exact: true }).tap();
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await expect(cleanup).toHaveCount(0);
  await page
    .getByRole("button", {
      name: "Audio cleanup · kept & flagged recordings",
      exact: true,
    })
    .tap();
  await expect(cleanup).toContainText("2 audio kept · 2 audio flagged");
  await expect(cleanup).toContainText("when you shut down the app");
  const partial = cleanup.locator("article").filter({ hasText: "03:00–04:00" });
  await expect(
    partial.getByRole("button", { name: "Keep this audio", exact: true }),
  ).toBeEnabled();
  await cleanup
    .getByRole("combobox", { name: "Show audio recordings" })
    .selectOption("keep");
  await expect(cleanup.locator("article")).toHaveCount(2);
  await expect(cleanup).toContainText("musical-evidence score 98/100");
  await expect(cleanup).toContainText(
    "notes: 98.0/100 · timing: 95.0/100 · dynamics: 90.0/100",
  );
  takes[3].action = "review";
  takes[3].reason = "Uncertain audio: retained for manual review.";
  await cleanup
    .getByRole("combobox", { name: "Show audio recordings" })
    .selectOption("review");
  await expect(cleanup.locator("article")).toHaveCount(1);
  await expect(cleanup).toContainText("Audio needs review");
  takes[3].action = "remove";
  await cleanup
    .getByRole("combobox", { name: "Show audio recordings" })
    .selectOption("flagged");
  await cleanup.screenshot({
    path: `/tmp/chopin-recording-cleanup-${test.info().project.name}.png`,
  });
  await cleanup
    .getByRole("button", { name: "Delete audio", exact: true })
    .first()
    .tap();
  const dialog = page.getByRole("alertdialog", { name: "Delete this audio?" });
  await expect(dialog).toContainText("02:00–03:00");
  await expect(dialog).toContainText(
    "MIDI files, MIDI exports, analyses and session history are retained",
  );
  await expect(cleanup).toContainText("MIDI sessions are kept indefinitely");
  expect(requests).toEqual([]);
  await dialog
    .getByRole("button", { name: "Delete permanently", exact: true })
    .tap();
  await expect(cleanup).toContainText("2 audio kept · 1 audio flagged");
  expect(requests).toEqual([
    { method: "DELETE", body: { confirmation: "delete", revision: 1 } },
  ]);
});

test("deleting attached audio through the GUI preserves actual MIDI and its session", async ({
  page,
}) => {
  const csv =
    "0, 0, Header, 0, 1, 480\n1, 0, Start_track\n1, 0, Tempo, 500000\n1, 0, Note_on_c, 0, 60, 80\n1, 240, Note_off_c, 0, 60, 0\n1, 480, Note_on_c, 0, 64, 80\n1, 720, Note_off_c, 0, 64, 0\n1, 960, Note_on_c, 0, 67, 80\n1, 1200, Note_off_c, 0, 67, 0\n1, 1440, End_track\n0, 0, End_of_file\n";
  const imported = await page.request.post("/api/import/midi", {
    multipart: {
      file: {
        name: "AudioOnlyCleanupRegression.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(csv),
      },
    },
  });
  expect(imported.ok()).toBeTruthy();
  const session = (await imported.json()).id;
  let segment: any;
  await expect
    .poll(async () => {
      const rows = await (
        await page.request.get(`/api/sessions/${session}/segments`)
      ).json();
      segment = rows[0];
      return !!segment;
    })
    .toBeTruthy();
  await expect
    .poll(async () =>
      (await (await page.request.get("/api/jobs")).json()).some((job: any) =>
        ["queued", "running"].includes(job.status),
      ),
    )
    .toBe(false);
  const original = await (
    await page.request.get(`/api/sessions/${session}/midi`)
  ).body();
  // A short valid AP-470-format WAV fixture, without opening any recording device.
  const frames = 4410,
    size = frames * 4,
    wav = Buffer.alloc(44 + size);
  wav.write("RIFF", 0);
  wav.writeUInt32LE(36 + size, 4);
  wav.write("WAVEfmt ", 8);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(2, 22);
  wav.writeUInt32LE(44100, 24);
  wav.writeUInt32LE(176400, 28);
  wav.writeUInt16LE(4, 32);
  wav.writeUInt16LE(16, 34);
  wav.write("data", 36);
  wav.writeUInt32LE(size, 40);
  const attached = await page.request.post(
    `/api/segments/${segment.id}/audio`,
    {
      multipart: {
        file: { name: "take.wav", mimeType: "audio/wav", buffer: wav },
      },
    },
  );
  expect(attached.ok()).toBeTruthy();
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await page
    .getByRole("button", {
      name: "Audio cleanup · kept & flagged recordings",
      exact: true,
    })
    .tap();
  const row = page.locator(`[data-audio-segment-id="${segment.id}"]`);
  await page
    .getByRole("combobox", { name: "Show audio recordings" })
    .selectOption("all");
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Delete audio", exact: true }).tap();
  await page
    .getByRole("alertdialog", { name: "Delete this audio?" })
    .getByRole("button", { name: "Delete permanently", exact: true })
    .tap();
  await expect(row).toHaveCount(0);
  const downloaded = await page.request.get(`/api/sessions/${session}/midi`);
  expect(downloaded.ok()).toBeTruthy();
  expect(await downloaded.body()).toEqual(original);
  expect(
    (await page.request.get(`/api/segments/${segment.id}/midi`)).ok(),
  ).toBeTruthy();
  expect(
    (
      await (await page.request.get(`/api/sessions/${session}/segments`)).json()
    ).some((s: any) => s.id === segment.id && !s.recording_deleted),
  ).toBe(true);
  const sessions = await (await page.request.get("/api/sessions")).json();
  const kept = sessions.find((s: any) => s.id === session);
  expect(kept).toBeTruthy();
  await expect(
    page
      .getByRole("button")
      .filter({ hasText: kept.name.replaceAll("_", " ") }),
  ).toBeVisible();
});

test("slow audio inventory requests do not accumulate refreshes", async ({
  page,
}) => {
  let requests = 0;
  let release!: () => void;
  const waiting = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/recordings", async (route) => {
    requests++;
    await waiting;
    await route.fulfill({
      json: { takes: [], sessions: [], policy: "two takes" },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await page
    .getByRole("button", {
      name: "Audio cleanup · kept & flagged recordings",
      exact: true,
    })
    .tap();
  await expect.poll(() => requests).toBe(1);
  await expect(page.getByText("Loading audio recordings…")).toBeVisible();
  // Cross the old four-second polling interval while the first request is pending.
  await page.waitForTimeout(4500);
  expect(requests).toBe(1);
  release();
  await expect(
    page.getByText("No stored audio in this view.", { exact: false }),
  ).toBeVisible();
  await expect.poll(() => requests, { timeout: 7000 }).toBe(2);
});
