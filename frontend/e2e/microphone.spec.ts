import { test, expect } from "@playwright/test";

test("recording sources are independent and fixed during a session", async ({
  page,
}) => {
  let active: string | null = null;
  let sources = { midi_enabled: true, microphone_enabled: false };
  const requests: unknown[] = [];
  await page.route("**/api/status", async (route) => {
    await route.fulfill({
      json: {
        active,
        ...sources,
        duration: 3,
        events: 0,
        devices: [],
        connected: null,
        error: null,
        notes: {},
        pedals: {},
        recent: [],
        queue_depth: 0,
        saving: false,
        simulation: false,
      },
    });
  });
  await page.route("**/api/record/start", async (route) => {
    const body = route.request().postDataJSON();
    requests.push(body);
    sources = body;
    active = "microphone-fixture";
    await route.fulfill({ json: { id: active } });
  });
  await page.goto("/");
  const midi = page.getByRole("checkbox", { name: "Record cable MIDI" });
  const mic = page.getByRole("checkbox", { name: "Record laptop microphone" });
  const record = page.getByRole("button", {
    name: "Record session",
    exact: true,
  });
  await expect(midi).toBeChecked();
  await expect(mic).not.toBeChecked();
  await midi.uncheck();
  await expect(record).toBeDisabled();
  await mic.check();
  await expect(record).toBeEnabled();
  await record.click();
  await expect(mic).toBeDisabled();
  await expect(midi).toBeDisabled();
  expect(requests).toEqual([
    {
      midi_enabled: false,
      microphone_enabled: true,
      microphone_device: "default",
    },
  ]);
  await expect(mic).toBeChecked();
  await expect(midi).not.toBeChecked();
});

test("microphone review shows matched attacks and uses saved activity bounds", async ({
  page,
}) => {
  const session = {
    id: "mic-review",
    name: "Microphone review fixture",
    started: "2026-11-09T10:00:00Z",
    status: "saved",
    duration: 15,
    events: 20,
    error: null,
  };
  const segment = {
    id: "a".repeat(32),
    session_id: session.id,
    start: 1,
    end: 12,
    piece_id: null,
    label: "Unknown piece",
    confidence: 0,
    kind: "unknown",
    revision: 1,
    discarded: false,
    complete: false,
    details: "{}",
  };
  const analysis = {
    id: "mic-analysis",
    session_id: session.id,
    segment_id: segment.id,
    created: session.started,
    result: {
      notes: 10,
      observations: [],
      audio: {
        available: true,
        rms_dbfs: -24,
        peak_dbfs: -5,
        clipped_sample_fraction: 0,
        acoustic_attacks: 8,
        coverage_seconds: 11,
        notice: "Microphone levels are not calibrated loudness.",
        correlation: {
          status: "estimated",
          audio_minus_midi_seconds: 0.12,
          matched_groups: 8,
          midi_groups: 10,
          median_absolute_residual_ms: 8,
          notice: "Residuals are not performance timing errors.",
          events: [
            {
              midi_time: 2,
              audio_time: 2.12,
              residual_ms: 8,
              attack_dbfs: -22,
              midi_velocity: 80,
            },
          ],
        },
      },
    },
  };
  await page.route("**/api/sessions", (route) =>
    route.fulfill({ json: [session] }),
  );
  await page.route(`**/api/sessions/${session.id}/summary`, (route) =>
    route.fulfill({ json: { notes: 10, markers: [] } }),
  );
  await page.route(`**/api/sessions/${session.id}/segments`, (route) =>
    route.fulfill({ json: [segment] }),
  );
  await page.route(`**/api/sessions/${session.id}/analyses`, (route) =>
    route.fulfill({ json: [analysis] }),
  );
  await page.route(`**/api/sessions/${session.id}/reports`, (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route(`**/api/sessions/${session.id}/recording`, (route) =>
    route.fulfill({ json: { microphone: { filename: "microphone.flac" } } }),
  );
  await page.route(`**/api/segments/${segment.id}/audio-status`, (route) =>
    route.fulfill({ json: { microphone: true, rendered_audio_count: 0 } }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await page.getByRole("button").filter({ hasText: session.name }).tap();
  const evidence = page.getByRole("region", {
    name: "Selected activity analysis",
  });
  await expect(evidence).toContainText("8/10 attack groups matched");
  await expect(evidence).toContainText("120 ms");
  await evidence
    .getByText("Correlated attacks (session timestamps)", { exact: true })
    .click();
  await expect(
    evidence.getByRole("cell", { name: "2.120", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Download activity FLAC" }),
  ).toHaveAttribute("href", `/api/segments/${segment.id}/microphone`);
  await evidence.screenshot({
    path: `/tmp/chopin-microphone-${test.info().project.name}.png`,
  });
  await page
    .getByRole("spinbutton", { name: "Segment end seconds" })
    .fill("10");
  await expect(
    page.getByRole("link", { name: "Download activity FLAC" }),
  ).toHaveCount(0);
});
