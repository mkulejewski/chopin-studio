import { execFileSync } from "node:child_process";
import type { NoteGroup } from "../src/AnalysisEvidence";
import { test, expect } from "@playwright/test";

test("session review shows only the selected activity's newest analysis", async ({
  page,
}) => {
  const session = {
    id: "evidence-fixture",
    name: "Evidence review fixture",
    started: "2026-11-06T10:00:00Z",
    duration: 60,
    events: 80,
    status: "imported",
    error: null,
  };
  const segments = ["n9-1", "n9-2", null].map((piece_id, i) => ({
    id: `activity-${i}`,
    piece_id,
    session_id: session.id,
    start: i * 20,
    end: (i + 1) * 20,
    revision: 1,
    discarded: false,
    complete: false,
    kind: "partial",
    confidence: 0.8,
    label: `Passage ${i}`,
    first_measure: 1,
    last_measure: 2,
  }));
  test.setTimeout(60000);
  const groups: NoteGroup[] = Array.from({ length: 240 }, (_, i) => ({
    measure: Math.floor(i / 4) + 1,
    beat: i * 0.5,
    score_notes: [
      { pitch: 60, duration: 0.5, staff: 1 },
      { pitch: 64, duration: 0.5, staff: 1 },
    ],
    time: i,
    expected: [60, 64],
    observed: i === 0 ? [60, 65] : [60, 64],
  }));
  for (let i = 3; i < groups.length; i += 4) {
    groups[i].expected.unshift(48);
    groups[i].observed.unshift(48);
    groups[i].score_notes!.push({
      pitch: 48,
      duration: 0.5,
      staff: 1,
      part: 1,
      display_staff: 2,
      staff_source: "reference_clef",
      clef_sign: "F",
    });
  }
  const blue = {
    severity: "review" as const,
    reason: "possible_variant",
    explanation: "Possible adaptation or edition difference.",
  };
  groups[1] = {
    ...groups[1],
    key_fifths: -4,
    expected: [71, 75],
    observed: [71, 75],
    score_notes: [
      {
        pitch: 71,
        duration: 0.5,
        staff: 1,
        spelling: { step: "C", alter: -1, octave: 5 },
      },
      {
        pitch: 75,
        duration: 0.5,
        staff: 1,
        spelling: { step: "E", alter: -1, octave: 5 },
      },
    ],
  };
  const red = {
    severity: "error" as const,
    reason: "likely_wrong_chord",
    explanation:
      "Unrelated chord between stable anchors in a verified reference.",
  };
  groups[0].musical_context = {
    expected: { "64": blue },
    observed: { "65": blue },
  };
  groups[5] = {
    ...groups[5],
    expected: [60, 64, 67],
    observed: [61, 65, 68],
    score_notes: [60, 64, 67].map((pitch) => ({
      pitch,
      duration: 0.5,
      staff: 1,
    })),
    musical_context: {
      expected: { "60": red, "64": red, "67": red },
      observed: { "61": red, "65": red, "68": red },
    },
  };
  groups[10] = {
    ...groups[10],
    expected: [60, 64, 67],
    observed: [60, 67],
    score_notes: [60, 64, 67].map((pitch) => ({
      pitch,
      duration: 0.5,
      staff: 1,
    })),
    musical_context: { expected: { "64": blue }, observed: {} },
  };
  const analysis = (
    segment: (typeof segments)[number],
    id: string,
    created: string,
    notes: number,
  ) => ({
    id,
    created,
    session_id: session.id,
    segment_id: segment.id,
    result: {
      key_fifths: -4,
      notes,
      segment_snapshot: segment,
      reference_quality: "provisional",
      note_comparison: id === "other" ? undefined : groups,
      musical_review: {
        version: "musical-context-v1",
        red_pitch_differences: 6,
        blue_pitch_differences: 3,
        timing_flags: [],
        notice: "Conservative local musical rules.",
      },
      observations: groups.flatMap((g, i) => [
        ...g.expected
          .filter((p) => !g.observed.includes(p))
          .map((pitch) => ({
            ...g,
            id: `${i}-missing-${pitch}`,
            kind: "missing",
            pitch,
            musical_judgement: g.musical_context?.expected[String(pitch)],
          })),
        ...g.observed
          .filter((p) => !g.expected.includes(p))
          .map((pitch) => ({
            ...g,
            id: `${i}-extra-${pitch}`,
            kind: "extra",
            pitch,
            musical_judgement: g.musical_context?.observed[String(pitch)],
          })),
      ]),
    },
  });
  await page.route("**/api/sessions", (route) =>
    route.fulfill({ json: [session] }),
  );
  await page.route(`**/api/sessions/${session.id}/summary`, (route) =>
    route.fulfill({ json: { notes: 80, markers: [] } }),
  );
  await page.route(`**/api/sessions/${session.id}/segments`, (route) =>
    route.fulfill({ json: segments }),
  );
  await page.route(`**/api/sessions/${session.id}/analyses`, (route) =>
    route.fulfill({
      json: [
        analysis(segments[1], "other", "2026-11-06T12:00:00Z", 222),
        analysis(segments[0], "latest", "2026-11-06T11:00:00Z", 111),
        analysis(segments[0], "old", "2026-11-06T10:00:00Z", 999),
      ],
    }),
  );
  await page.route(`**/api/sessions/${session.id}/reports`, (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  await page.getByRole("button").filter({ hasText: session.name }).tap();
  const evidence = page.getByRole("region", {
    name: "Selected activity analysis",
  });
  await expect(evidence).toHaveCount(1);
  await expect(
    evidence.getByRole("combobox", { name: "Comparison method", exact: true }),
  ).toHaveValue("musical");
  const editor = page.getByRole("heading", { name: "Edit selected activity" });
  expect(
    await editor.evaluate(
      (el) =>
        !!(
          el.compareDocumentPosition(
            document.querySelector(".analysis-evidence")!,
          ) & Node.DOCUMENT_POSITION_FOLLOWING
        ),
    ),
  ).toBe(true);
  const navigation = evidence.getByRole("navigation", {
    name: "Comparison note navigation",
  });
  expect(
    await navigation.evaluate(
      (el) =>
        !!(
          el.compareDocumentPosition(
            document.querySelector(".note-overlay-scroll")!,
          ) & Node.DOCUMENT_POSITION_FOLLOWING
        ),
    ),
  ).toBe(true);
  await expect(evidence.locator(".analysis-metrics")).toContainText("111");
  await expect(evidence.locator(".analysis-metrics")).not.toContainText("999");
  await evidence.getByRole("button", { name: /^Measure 1, group 1:/ }).tap();
  await expect(evidence.getByRole("status")).toContainText("Expected: C4, E♮4");
  await expect(evidence.getByRole("status")).toContainText("Played: C4, F4");
  await evidence.getByRole("button", { name: /^Measure 1, group 2:/ }).tap();
  await expect(evidence.getByRole("status")).toContainText(
    "Expected: C♭5, E♭5",
  );
  await expect(evidence.getByRole("status")).toContainText("Played: C♭5, E♭5");
  await evidence.screenshot({
    path: `/tmp/chopin-analysis-panel-${test.info().project.name}.png`,
  });
  const staff = evidence.getByRole("region", {
    name: "Staff score comparison",
  });
  expect(
    await staff.evaluate(
      (el) =>
        !!(
          el.compareDocumentPosition(
            document.querySelector(
              '[aria-label="Comparison note navigation"]',
            )!,
          ) & Node.DOCUMENT_POSITION_FOLLOWING
        ),
    ),
  ).toBe(true);
  await staff.getByRole("button", { name: "Render score comparison" }).tap();
  await expect(staff.getByRole("status")).toHaveText("Score comparison ready.");
  await expect(staff.locator("svg").first()).toBeVisible();
  const xmlUrl = await staff
    .getByRole("link", { name: "Download comparison MusicXML" })
    .getAttribute("href");
  const xml = await page.evaluate(
    async (url) => (await fetch(url!)).text(),
    xmlUrl,
  );
  expect(xml).toContain("<key><fifths>-4</fifths></key>");
  expect(xml).toContain("<step>C</step><alter>-1</alter><octave>5</octave>");
  expect(xml).toContain("<step>E</step><alter>-1</alter><octave>5</octave>");
  expect(
    await staff
      .locator(
        '[fill="#C1273D"], [fill="#c1273d"], [stroke="#C1273D"], [stroke="#c1273d"]',
      )
      .count(),
  ).toBeGreaterThan(0);
  await staff.locator(".staff-comparison-scroll").screenshot({
    path: `/tmp/chopin-staff-overlay-${test.info().project.name}.png`,
  });
  await staff.getByRole("combobox").selectOption("stacked");
  await expect(staff.getByRole("status")).toHaveText("Score comparison ready.");
  await expect(
    staff.getByRole("link", { name: "Download comparison MusicXML" }),
  ).toHaveAttribute("download", "pitch-comparison-stacked.musicxml");
  await staff.locator(".staff-comparison-scroll").screenshot({
    path: `/tmp/chopin-staff-stacked-${test.info().project.name}.png`,
  });
  await evidence
    .getByRole("combobox", { name: "Comparison method", exact: true })
    .selectOption("musical");
  await expect(staff.getByRole("status")).toHaveText("Score comparison ready.");
  expect(
    await staff.locator('[fill="#2364B4"], [fill="#2364b4"]').count(),
  ).toBeGreaterThan(0);
  expect(
    await staff.locator('[fill="#C1273D"], [fill="#c1273d"]').count(),
  ).toBeGreaterThan(0);
  await expect(evidence.locator(".note-review-missing")).toHaveCount(2);
  await staff.locator(".staff-comparison-scroll").screenshot({
    path: `/tmp/chopin-musical-context-${test.info().project.name}.png`,
  });
  await evidence.getByLabel("Measure to review").selectOption("2");
  await expect(staff.getByRole("status")).toHaveText("Score comparison ready.");
  const pendingDownload = page.waitForEvent("download");
  await staff
    .getByRole("button", { name: "Download full comparison PDF" })
    .tap();
  await expect(staff.locator(".pdf-export-status")).toContainText(
    "Downloaded full comparison PDF",
    { timeout: 30000 },
  );
  const downloaded = await pendingDownload;
  expect(downloaded.suggestedFilename()).toMatch(/-musical-stacked\.pdf$/);
  const pdfPath = `/tmp/chopin-comparison-${test.info().project.name}.pdf`;
  await downloaded.saveAs(pdfPath);
  const info = JSON.parse(
    execFileSync(
      "../.venv/bin/python",
      [
        "-c",
        "import json,sys;from pypdf import PdfReader;r=PdfReader(sys.argv[1]);print(json.dumps({'pages':len(r.pages),'text':' '.join(p.extract_text() for p in r.pages)}))",
        pdfPath,
      ],
      { encoding: "utf8" },
    ),
  );
  expect(info.pages).toBeGreaterThan(1);
  expect(info.text).toContain("Entire activity: 240 groups");
  expect(info.text).toMatch(/m\.\s*60\b/);
  expect(info.text).toContain("Musical context");
  await evidence.getByLabel("Measure to review").selectOption("all");
  await staff.getByRole("button", { name: "Hide staff comparison" }).tap();
  await evidence
    .getByRole("combobox", { name: "Comparison method", exact: true })
    .selectOption("strict");
  await evidence.getByRole("button", { name: "Next notes" }).tap();
  await expect(evidence).toContainText("Page 2 of 10");
  await evidence.getByLabel("Measure to review").selectOption("2");
  await expect(evidence).toContainText("Page 1 of 1");
  await page.screenshot({
    path: `/tmp/chopin-analysis-${test.info().project.name}.png`,
    fullPage: true,
  });
  await page.getByLabel("Segment end seconds").fill("19");
  await expect(evidence.getByRole("status")).toContainText(
    "predates activity edits",
  );
  await page
    .getByRole("combobox", { name: "Piece", exact: true })
    .selectOption("n9-2");
  await expect(evidence).toHaveCount(0);
  await page.locator(".timeline-item").nth(1).tap();
  await expect(evidence).toHaveCount(1);
  await expect(evidence.locator(".analysis-metrics")).toContainText("222");
  await expect(evidence).toContainText(
    "This saved analysis has no note overlay",
  );
  await page.locator(".timeline-item").nth(2).tap();
  await expect(evidence).toHaveCount(0);
  await expect(
    page.getByText("No saved analysis for this activity", { exact: false }),
  ).toBeVisible();
});
