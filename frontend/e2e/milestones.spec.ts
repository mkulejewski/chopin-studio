import { test, expect } from "@playwright/test";
import { musicXml, midiFixture } from "./music-fixture";
import { scorePdf } from "./pdf-fixture";

test("touch reference verification, timeline correction, analysis, local report and optional audio", async ({
  page,
}) => {
  test.setTimeout(60000);
  // Original test-only materials, not a claim that these notes are Chopin.
  await page.request.post("/api/volumes/nocturnes/pdf", {
    multipart: {
      file: {
        name: "synthetic.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(),
      },
    },
  });
  const library = await (await page.request.get("/api/library")).json();
  const piece = library.pieces.find((p: any) => p.id === "n9-1");
  await page.request.put("/api/pieces/n9-1", {
    data: { ...piece, start_page: 1, end_page: 3 },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  const referencePanel = page.locator(".reference-manager");
  await referencePanel
    .getByRole("combobox", { name: "Reference piece", exact: true })
    .selectOption("n9-1");
  const referenceChooser = page.waitForEvent("filechooser");
  await referencePanel
    .getByRole("button", { name: "Import MusicXML / MXL" })
    .tap();
  await (
    await referenceChooser
  ).setFiles({
    name: "original-fixture.musicxml",
    mimeType: "application/xml",
    buffer: musicXml(),
  });
  await expect(
    referencePanel.getByRole("button", { name: "Review reference" }).last(),
  ).toBeVisible();
  await referencePanel
    .getByRole("button", { name: "Review reference" })
    .last()
    .tap();
  await referencePanel
    .getByRole("button", { name: "Preview symbolic score" })
    .tap();
  await expect(
    referencePanel.locator(".symbolic-preview svg").first(),
  ).toBeVisible();
  await referencePanel.getByLabel("Quality status").selectOption("verified");
  await referencePanel
    .getByRole("button", { name: "Save reference review" })
    .tap();
  await referencePanel.getByRole("button", { name: "Close review" }).tap();
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  const chooser = page.waitForEvent("filechooser");
  await page
    .getByRole("button", { name: "Import MIDI / CSV", exact: true })
    .tap();
  await (
    await chooser
  ).setFiles({
    name: "milestone-fixture.mid",
    mimeType: "audio/midi",
    buffer: midiFixture(),
  });
  await expect(
    page.getByText("Imported successfully. The original file is preserved."),
  ).toBeVisible();
  await page
    .getByRole("button")
    .filter({
      has: page.getByRole("heading", { name: /Imported milestone-fixture/ }),
    })
    .first()
    .tap();
  await expect(
    page.getByRole("heading", { name: "Your activity timeline" }),
  ).toBeVisible();
  await expect(page.locator(".timeline-item").first()).toBeVisible();
  await page.locator(".timeline-item").first().tap();
  const before = await page.locator(".timeline-item").count();
  await page.getByRole("button", { name: "Split activity", exact: true }).tap();
  await page.getByRole("button", { name: "Save timeline edits" }).tap();
  await expect(page.locator(".timeline-item")).toHaveCount(before + 1);
  await page.getByRole("button", { name: "Undo last timeline edit" }).tap();
  await expect(page.locator(".timeline-item")).toHaveCount(before);
  await page.locator(".timeline-item").first().tap();
  await page
    .getByRole("button", { name: "Analyse activity", exact: true })
    .tap();
  await expect(
    page.getByRole("heading", { name: "Evidence, with context" }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Generate local report" }).tap();
  await expect(page.locator(".report-text").first()).toContainText(
    "local practice report",
  );
  const midiLink = page.getByRole("link", { name: "Export activity MIDI" });
  const midi = await page.request.get((await midiLink.getAttribute("href"))!);
  expect((await midi.body()).subarray(0, 4).toString()).toBe("MThd");
  const engines = await (await page.request.get("/api/audio/engines")).json();
  if (engines.fluidsynth && engines.soundfonts.length) {
    await page
      .getByRole("button", { name: "Render this activity with FluidSynth" })
      .tap();
    await expect(page.locator("audio").first()).toBeVisible();
    const src = await page.locator("audio").first().getAttribute("src");
    const audio = await page.request.get(src!);
    expect(audio.status()).toBe(200);
    await page
      .locator("audio")
      .first()
      .tap({ position: { x: 30, y: 27 } });
    await expect
      .poll(() =>
        page
          .locator("audio")
          .first()
          .evaluate((element: HTMLAudioElement) => element.paused),
      )
      .toBe(false);
  }
  await page.getByRole("button", { name: "Practice", exact: true }).tap();
  await page.getByRole("button", { name: "Live controls" }).tap();
  await page.getByLabel("Enable live piece recognition").check();
  await expect(
    page.getByText("Live recognition · experimental", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Enable live piece recognition").uncheck();
  await page.screenshot({
    path: `/tmp/chopin-milestones-${page.viewportSize()!.width}.png`,
    fullPage: true,
  });
});
