import { test, expect } from "@playwright/test";
import { musicXml, pitches } from "./music-fixture";
import { scorePdf } from "./pdf-fixture";

test("calibrate PDF pages and follow real simulated bass MIDI with inferred tempo", async ({
  page,
}) => {
  test.setTimeout(60000);
  const settings = await (await page.request.get("/api/settings")).json();
  await page.request.put("/api/settings", {
    data: {
      ...settings,
      live_enabled: false,
      live_auto_turn: true,
      live_allow_provisional: true,
      live_piece_id: "n9-1",
    },
  });
  const pdf = await page.request.post("/api/volumes/nocturnes/pdf", {
    multipart: {
      file: {
        name: "following.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(),
      },
    },
  });
  expect(pdf.ok()).toBeTruthy();
  const library = await (await page.request.get("/api/library")).json();
  const piece = library.pieces.find((p: any) => p.id === "n9-1");
  await page.request.put("/api/pieces/n9-1", {
    data: { ...piece, start_page: 1, end_page: 3 },
  });
  await page.request.put("/api/pieces/n9-1/pages", { data: [] });
  await page.request.put("/api/pieces/n9-1/view", {
    data: { page: 1, zoom: 1, two_pages: false, crop: 0 },
  });
  const xml = Buffer.from(
    musicXml()
      .toString()
      .replace(
        /<octave>(\d+)<\/octave>/g,
        (_, octave) => `<octave>${Number(octave) - 2}</octave>`,
      ),
  );
  const imported = await page.request.post("/api/pieces/n9-1/references", {
    multipart: {
      file: { name: "bass.musicxml", mimeType: "application/xml", buffer: xml },
    },
  });
  expect(imported.ok()).toBeTruthy();
  let csv = "0, 0, Header, 0, 1, 480\n1, 0, Start_track\n1, 0, Tempo, 500000\n";
  pitches.forEach((pitch, i) => {
    csv += `1, ${i * 480}, Note_on_c, 0, ${pitch - 24}, 80\n1, ${i * 480 + 240}, Note_off_c, 0, ${pitch - 24}, 0\n`;
  });
  csv += "1, 9600, End_track\n0, 0, End_of_file\n";
  const take = await page.request.post("/api/import/midi", {
    multipart: {
      file: {
        name: "bass.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(csv),
      },
    },
  });
  expect(take.ok()).toBeTruthy();
  const session = await take.json();
  await page.addInitScript(() => localStorage.setItem("chopin-piece", "n9-1"));
  await page.goto("/");
  await expect(
    page.getByLabel("Score PDF page 1", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Calibrate page", exact: true }).tap();
  for (let pdfPage = 1; pdfPage <= 3; pdfPage++) {
    await page.getByLabel("First displayed page").fill(String(pdfPage));
    await page
      .getByLabel("Page calibration measure")
      .fill(String(pdfPage * 2 - 1));
    await page
      .getByRole("button", { name: "Save this page link", exact: true })
      .tap();
    await expect(
      page.getByText(
        `Saved: measure ${pdfPage * 2 - 1} starts PDF page ${pdfPage}.`,
        { exact: true },
      ),
    ).toBeVisible();
  }
  const links = await (await page.request.get("/api/pieces/n9-1/pages")).json();
  expect(
    links.map(({ measure, pdf_page }: any) => ({ measure, pdf_page })),
  ).toEqual([
    { measure: 1, pdf_page: 1 },
    { measure: 3, pdf_page: 2 },
    { measure: 5, pdf_page: 3 },
  ]);
  await page.screenshot({
    path: `/tmp/chopin-calibration-${page.viewportSize()!.width}.png`,
    fullPage: true,
  });
  await page.request.put("/api/pieces/n9-1/view", {
    data: { page: 1, zoom: 1, two_pages: true, crop: 0 },
  });
  await page.request.put("/api/settings", {
    data: {
      ...settings,
      live_enabled: true,
      live_auto_turn: true,
      live_allow_provisional: true,
      live_piece_id: "n9-1",
    },
  });
  await page.reload();
  const simulation = await page.request.post("/api/simulation/start", {
    data: { session_id: session.id, speed: 1 },
  });
  expect(simulation.ok()).toBeTruthy();
  try {
    await expect(page.locator(".paper-pair canvas").first()).toHaveAttribute(
      "aria-label",
      "Score PDF page 2",
      { timeout: 15000 },
    );
    await expect(page.locator(".live-summary")).toContainText(
      "♩ = 120 (bass notes)",
    );
    await page
      .getByRole("button", { name: "Calibrate page", exact: true })
      .tap();
    await expect
      .poll(
        async () =>
          (await (await page.request.get("/api/live")).json()).page_request
            ?.page,
        { timeout: 10000 },
      )
      .toBe(3);
    await expect(
      page.getByLabel("Score PDF page 2", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Calibrate page", exact: true })
      .tap();
    await expect(page.locator(".paper-pair canvas").first()).toHaveAttribute(
      "aria-label",
      "Score PDF page 3",
      { timeout: 10000 },
    );
    await expect(page.locator(".live-summary")).toContainText(
      "provisional reference",
    );
    await page.screenshot({
      path: `/tmp/chopin-following-${page.viewportSize()!.width}.png`,
      fullPage: true,
    });
  } finally {
    await page.request.post("/api/simulation/stop");
    await page.request.put("/api/settings", { data: settings });
  }
});
