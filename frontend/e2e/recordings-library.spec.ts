import { test, expect } from "@playwright/test";

test("recordings are grouped by piece and Learning stays outside Analysis", async ({
  page,
}) => {
  const makeSession = (id: string, source: string) => ({
    id,
    source,
    name: `${id} recording`,
    started: "2026-11-13T10:00:00Z",
    status: "saved",
    duration: 60,
    events: 80,
    error: null,
    audio_sources: [],
  });
  const practice = {
    ...makeSession("practice", "live"),
    status: "incomplete",
    error:
      "Microphone stopped unexpectedly or reported capture errors: arecord: pcm_read:2240: read error: Interrupted system call",
  };
  const learning = {
    ...makeSession("lesson", "learning"),
    audio_sources: [
      { label: "Recorded microphone", url: "/api/sessions/lesson/microphone" },
    ],
    learning_piece_id: "e25-1",
    learning_piece_title: "Aeolian Harp",
  };
  const unknown = {
    ...makeSession("unidentified", "import"),
    audio_sources: [
      {
        label: "Recorded microphone",
        url: "/api/sessions/unidentified/microphone",
      },
    ],
  };
  const sessions = [practice, learning, unknown];
  const segments = [
    {
      id: "nocturne",
      session_id: practice.id,
      piece_id: "n9-1",
      start: 0,
      end: 30,
      kind: "complete",
      discarded: false,
      audio_sources: [
        {
          label: "Recorded microphone",
          url: "/api/segments/nocturne/microphone",
        },
        { label: "Rendered MIDI audio", url: "/api/audio/rendered-fixture" },
      ],
      revision: 1,
      confidence: 1,
      label: "Nocturne",
      complete: true,
    },
    {
      id: "removed",
      session_id: practice.id,
      piece_id: "n9-2",
      start: 30,
      end: 60,
      kind: "partial",
      discarded: true,
      audio_sources: [],
      revision: 1,
      confidence: 1,
      label: "Nocturne 2",
      complete: false,
    },
  ];
  await page.route("**/api/sessions", (route) =>
    route.fulfill({ json: sessions }),
  );
  await page.route("**/api/recordings/library", (route) =>
    route.fulfill({ json: { sessions, segments } }),
  );
  for (const session of sessions) {
    await page.route(`**/api/sessions/${session.id}/summary`, (route) =>
      route.fulfill({ json: { notes: 40, markers: [] } }),
    );
    await page.route(`**/api/sessions/${session.id}/segments`, (route) =>
      route.fulfill({
        json: segments.filter((s) => s.session_id === session.id),
      }),
    );
    for (const endpoint of ["analyses", "reports"])
      await page.route(`**/api/sessions/${session.id}/${endpoint}`, (route) =>
        route.fulfill({ json: [] }),
      );
    await page.route(`**/api/sessions/${session.id}/recording`, (route) =>
      route.fulfill({ json: { microphone: null, timeline_locked: false } }),
    );
  }
  await page.route("**/api/segments/nocturne/audio-status", (route) =>
    route.fulfill({ json: { microphone: false } }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await expect(
    page.getByRole("button", { name: "Score Library", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("button", { name: "Recordings Library", exact: true })
    .tap();
  const library = page.getByRole("region", {
    name: "Recordings Library",
    exact: true,
  });
  await expect(library.locator(".recording-piece-card")).toHaveCount(3);
  await library.getByLabel("Find a recorded piece").fill("Op 9 No 1");
  await expect(library.locator(".recording-piece-card")).toHaveCount(1);
  await library
    .locator(".recording-piece-card")
    .getByRole("button", { name: "Open recordings" })
    .tap();
  await expect(
    library.getByRole("link", { name: "Download MIDI" }),
  ).toHaveAttribute("href", "/api/segments/nocturne/midi");
  await library.getByRole("button", { name: "Listen to recording" }).tap();
  await expect(library.getByLabel("Recorded microphone")).toHaveAttribute(
    "src",
    "/api/segments/nocturne/microphone",
  );
  await expect(library.getByLabel("Rendered MIDI audio")).toHaveAttribute(
    "src",
    "/api/audio/rendered-fixture",
  );
  await expect(library.getByText(practice.error)).toHaveCount(0);
  const card = library.locator(".recording-detail-card");
  const spacing = await card.evaluate((el) => ({
    padding: parseFloat(getComputedStyle(el).paddingLeft),
    lineHeight: parseFloat(
      getComputedStyle(el.querySelector(".recording-passage")!).lineHeight,
    ),
  }));
  expect(spacing.padding).toBeGreaterThanOrEqual(22);
  expect(spacing.lineHeight).toBeGreaterThanOrEqual(24);
  await expect(library.locator(".recording-capture-warning")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await library.locator(".recording-detail-card").screenshot({
    path: `/tmp/chopin-recording-details-${test.info().project.name}.png`,
  });
  await library
    .getByRole("button", { name: "Open in Analysis", exact: true })
    .tap();
  await expect(page.getByLabel("Select analysis session")).toHaveValue(
    practice.id,
  );
  await expect(page.getByLabel("Select analysis activity")).toHaveValue(
    "nocturne",
  );
  await expect(
    page.getByLabel("Select analysis session").locator("option"),
  ).toHaveCount(3);
  await expect(page.getByLabel("Select analysis session")).not.toContainText(
    "lesson recording",
  );
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await expect(
    library.getByRole("heading", { name: "practice recording" }),
  ).toBeVisible();
  await library.getByRole("button", { name: "All recorded pieces" }).tap();
  await library.getByLabel("Find a recorded piece").fill("");
  await expect(
    library.locator(".recording-piece-card").filter({ hasText: "Op 9 No 2" }),
  ).toHaveCount(0);
  await page.screenshot({
    path: `/tmp/chopin-recording-piece-cards-${test.info().project.name}.png`,
  });
  await library
    .locator(".recording-piece-card")
    .filter({ hasText: "Op 25 No 1" })
    .getByRole("button", { name: "Open recordings" })
    .tap();
  await expect(
    library.getByRole("button", { name: "Open in Analysis" }),
  ).toHaveCount(0);
  await library.getByRole("button", { name: "Review recording" }).tap();
  await expect(
    page.getByRole("button", { name: "Open session analysis" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Analyse activity", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Analysis", exact: true }).tap();
  await expect(page.getByLabel("Select analysis session")).toHaveValue("");
  await expect(
    page.getByRole("heading", { name: "Start with a saved performance." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await library.getByRole("button", { name: "All recorded pieces" }).tap();
  await library
    .locator(".recording-piece-card")
    .filter({ hasText: "Unidentified recordings" })
    .getByRole("button", { name: "Open recordings" })
    .tap();
  await expect(library).toContainText("unidentified recording");
  await expect(
    library.getByRole("link", { name: "Download MIDI" }),
  ).toHaveAttribute("href", "/api/sessions/unidentified/midi");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `/tmp/chopin-recordings-library-${test.info().project.name}.png`,
  });
  await page.route("**/api/recordings/library", (route) =>
    route.fulfill({ json: { sessions: [], segments: [] } }),
  );
  await library.getByRole("button", { name: "Refresh recordings" }).tap();
  await expect(
    library.getByText("No audio recordings remain for this piece.", {
      exact: false,
    }),
  ).toBeVisible();
  await library.getByRole("button", { name: "All recorded pieces" }).tap();
  await expect(
    library.getByText("No saved audio recordings yet.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Score Library", exact: true }).tap();
  await expect(
    page.getByRole("heading", { name: "Your score library." }),
  ).toBeVisible();
});
