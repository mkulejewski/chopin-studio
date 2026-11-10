import { test, expect } from "@playwright/test";
import { musicXml, pitches } from "./music-fixture";

test("library opens a piece's saved passages and returns from session review", async ({
  page,
}) => {
  const reference = await page.request.post("/api/pieces/n9-1/references", {
    multipart: {
      file: {
        name: "piece-sessions.musicxml",
        mimeType: "application/xml",
        buffer: musicXml(),
      },
    },
  });
  expect(reference.ok()).toBeTruthy();
  let csv = "0, 0, Header, 0, 1, 480\n1, 0, Start_track\n1, 0, Tempo, 500000\n";
  [...pitches, ...pitches].forEach((pitch, i) => {
    csv += `1, ${i * 480}, Note_on_c, 0, ${pitch}, 80\n1, ${i * 480 + 240}, Note_off_c, 0, ${pitch}, 0\n`;
  });
  csv += "1, 19200, End_track\n0, 0, End_of_file\n";
  const imported = await page.request.post("/api/import/midi", {
    multipart: {
      file: {
        name: "piece-centric-take.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(csv),
      },
    },
  });
  expect(imported.ok()).toBeTruthy();
  const session = await imported.json();
  await expect
    .poll(async () => {
      const rows = await (
        await page.request.get("/api/pieces/n9-1/sessions")
      ).json();
      return rows.find((s: any) => s.id === session.id)?.segments[0]?.kind;
    })
    .toBe("complete");
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await page.screenshot({
    path: `/tmp/chopin-library-${test.info().project.name}.png`,
  });
  await page
    .locator('[data-piece-id="n9-1"]')
    .getByRole("button", { name: "Saved sessions", exact: true })
    .tap();
  const panel = page.getByRole("region", {
    name: "Saved sessions for this piece",
  });
  const take = panel
    .locator("article")
    .filter({ hasText: "piece-centric-take" })
    .first();
  await expect(take).toBeVisible();
  await page.screenshot({
    path: `/tmp/chopin-piece-sessions-${test.info().project.name}.png`,
  });
  await take
    .getByRole("button", { name: /Review .*Complete performance/ })
    .tap();
  await expect(
    page.getByRole("heading", { name: "Edit selected activity" }),
  ).toBeVisible();
  await expect(page.getByLabel("Activity type")).toHaveValue("complete");
  await page.getByLabel("Activity type").selectOption("full_exercise");
  await page
    .getByRole("button", { name: "Save timeline edits", exact: true })
    .tap();
  await expect(page.getByLabel("Activity type")).toHaveValue("full_exercise");
  await page.getByRole("button", { name: /Back to .* saved sessions/ }).tap();
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Full-piece exercise");
  await panel
    .getByRole("button", { name: "Back to library", exact: true })
    .tap();
  await page
    .locator('[data-piece-id="n9-2"]')
    .getByRole("button", { name: "Saved sessions", exact: true })
    .tap();
  await expect(
    page.getByText("No saved sessions linked to this piece yet."),
  ).toBeVisible();
});
