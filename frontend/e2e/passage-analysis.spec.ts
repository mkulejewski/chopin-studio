import { test, expect } from "@playwright/test";
import { musicXml, pitches } from "./music-fixture";

test("score-aligned analysis, two takes and technical problem time", async ({
  page,
}) => {
  test.setTimeout(60000);
  const objectiveTitle = `Even inner voice · ${test.info().project.name}`;
  const importedRef = await page.request.post("/api/pieces/n9-1/references", {
    multipart: {
      file: {
        name: "passages.musicxml",
        mimeType: "application/xml",
        buffer: musicXml(),
      },
    },
  });
  expect(importedRef.ok()).toBeTruthy();
  const ref = await importedRef.json();
  expect(
    (
      await page.request.put(`/api/references/${ref.id}`, {
        data: { quality: "verified", edition: "Synthetic browser fixture" },
      })
    ).ok(),
  ).toBeTruthy();
  const ids: string[] = [];
  for (const attempt of [0, 1]) {
    let csv =
      "0, 0, Header, 0, 1, 480\n1, 0, Start_track\n1, 0, Tempo, 500000\n1, 0, Control_c, 0, 64, 87\n";
    [...pitches, ...pitches].forEach((pitch, i) => {
      const tick = i * 480;
      csv += `1, ${tick}, Control_c, 0, 88, ${i % 128}\n1, ${tick}, Note_on_c, 0, ${pitch}, ${70 + attempt * 8}\n1, ${tick + 360}, Control_c, 0, 88, 12\n1, ${tick + 360}, Note_off_c, 0, ${pitch}, ${30 + (i % 8)}\n`;
    });
    csv += `1, ${pitches.length * 960}, End_track\n0, 0, End_of_file\n`;
    const response = await page.request.post("/api/import/midi", {
      multipart: {
        file: {
          name: `aligned-take-${attempt}.csv`,
          mimeType: "text/csv",
          buffer: Buffer.from(csv),
        },
      },
    });
    expect(response.ok()).toBeTruthy();
    ids.push((await response.json()).id);
  }
  const segments: any[] = [];
  for (const id of ids) {
    await expect
      .poll(
        async () =>
          (
            await (
              await page.request.get(`/api/sessions/${id}/analyses`)
            ).json()
          ).length,
        { timeout: 30000 },
      )
      .toBeGreaterThan(0);
    const rows = await (
      await page.request.get(`/api/sessions/${id}/segments`)
    ).json();
    segments.push(rows[0]);
  }
  await page.goto("/");
  await page.getByRole("button", { name: "Analysis", exact: true }).tap();
  await page.getByLabel("Select analysis session").selectOption(ids[0]);
  const measurements = page.getByRole("region", {
    name: "Synchronized passage measurements",
  });
  await expect(measurements).toBeVisible();
  await expect(measurements).toContainText("Release data: uncalibrated");
  await measurements
    .getByRole("button", { name: /m1 · beat/ })
    .first()
    .tap();
  await measurements
    .getByText("Individual note measurements", { exact: true })
    .tap();
  await expect(measurements).toContainText("14-bit 8960");
  await expect(page.getByText(/CC88 ordering:/)).toContainText(
    "80 paired prefixes",
  );
  await page
    .getByText("Compare different takes of a piece", { exact: true })
    .tap();
  const compare = page
    .getByRole("heading", { name: "Compare two attempts", exact: true })
    .locator("..");
  await compare
    .getByRole("combobox", { name: "First attempt", exact: true })
    .selectOption(segments[0].id);
  await compare
    .getByRole("combobox", { name: "Comparison attempt", exact: true })
    .selectOption(segments[1].id);
  await compare
    .getByRole("button", { name: "Compare measurements", exact: true })
    .tap();
  await expect(compare).toContainText("40 shared score positions");
  await expect(
    compare.getByRole("region", { name: "Synchronized passage measurements" }),
  ).toContainText("Second attempt: dashed purple");
  await compare
    .getByRole("combobox", { name: "Compare measure", exact: true })
    .selectOption("2");
  await expect(
    compare
      .getByRole("region", { name: "Synchronized passage measurements" })
      .getByRole("button", { name: /m1 · beat/ }),
  ).toHaveCount(0);
  await page.screenshot({
    path: `/tmp/chopin-passage-comparison-${test.info().project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Progress", exact: true }).tap();
  const summary = page.locator("summary").filter({
    hasText: /Measures, recurring mistakes, recall.*Nocturne 9 · No. 1$/,
  });
  await summary.tap();
  const progress = summary.locator("..");
  await expect(
    progress.getByRole("heading", {
      name: "Measure-level progress",
      exact: true,
    }),
  ).toBeVisible();
  await progress
    .getByLabel("New objective", { exact: true })
    .fill(objectiveTitle);
  await progress
    .getByRole("combobox", { name: "Skill", exact: true })
    .selectOption("voicing");
  await progress
    .getByRole("button", { name: "Add technical objective", exact: true })
    .tap();
  await expect(
    progress.getByText(objectiveTitle, { exact: true }).first(),
  ).toBeVisible();
  await progress
    .getByRole("combobox", { name: "Objective", exact: true })
    .last()
    .selectOption({ label: objectiveTitle });
  await progress
    .getByRole("combobox", { name: "Activity", exact: true })
    .selectOption(segments[0].id);
  await progress
    .getByRole("button", { name: "Attribute interval", exact: true })
    .tap();
  await expect(progress).toContainText("00:19 explicitly attributed");
  await page.screenshot({
    path: `/tmp/chopin-measure-progress-${test.info().project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("Practice auto-open waits for stable recognition and ignores assumptions", async ({
  page,
}) => {
  const previous = await (await page.request.get("/api/settings")).json();
  await page.request.put("/api/settings", {
    data: { ...previous, live_enabled: true, live_auto_open: true },
  });
  let stable = false,
    assumed = true;
  await page.route("**/api/live", (route) =>
    route.fulfill({
      json: {
        enabled: true,
        piece_id: "n9-2",
        confidence: 0.96,
        stable,
        assumed,
        label: "Synthetic recognition",
        measure: 2,
      },
    }),
  );
  await page.addInitScript(() => {
    localStorage.removeItem("chopin-learning-piece");
    localStorage.setItem("chopin-piece", "n72-1");
  });
  try {
    await page.goto("/");
    await expect(page.locator(".live-summary")).toContainText(
      "assuming open score",
    );
    expect(
      await page.evaluate(() => localStorage.getItem("chopin-piece")),
    ).toBe("n72-1");
    stable = true;
    await page
      .getByRole("button", { name: "Live controls", exact: true })
      .tap();
    await expect(
      page.getByLabel("Automatically open the recognised piece"),
    ).toBeChecked();
    expect(
      await page.evaluate(() => localStorage.getItem("chopin-piece")),
    ).toBe("n72-1");
    assumed = false;
    await expect
      .poll(() => page.evaluate(() => localStorage.getItem("chopin-piece")))
      .toBe("n9-2");
  } finally {
    await page.request.put("/api/settings", { data: previous });
  }
});
