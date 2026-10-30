import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test("touch-only recording survives navigation and requires stop confirmation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Record session", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Record session", exact: true }).tap();
  await expect(
    page.getByText("Session recording", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await expect(
    page.getByRole("button", { name: "Return to practice" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Session recording", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Stop session", exact: true }).tap();
  await page.getByRole("button", { name: "Keep recording" }).tap();
  await expect(
    page.getByText("Session recording", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Stop session", exact: true }).tap();
  await page.getByRole("button", { name: "Stop & save session" }).tap();
  await expect(
    page.getByRole("link", { name: "Export original MIDI" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "View MIDI measurements" }).tap();
  await expect(
    page.getByRole("heading", { name: "The shape of your touch" }),
  ).toBeVisible();
});

test("touch library filtering, favourites, learning and diagnostics", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await page
    .getByRole("combobox", { name: "Filter library" })
    .selectOption("Waltzes");
  await expect(
    page.getByRole("heading", { name: "Waltz", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit Waltz Op. 64 · No. 2" }).tap();
  await page.getByLabel("Practice status").selectOption("Learning");
  await page.getByRole("button", { name: "Save piece", exact: true }).tap();
  await page.getByRole("button", { name: "Open score", exact: true }).tap();
  await expect(
    page.getByRole("heading", { name: "Waltz in C-sharp minor" }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Hide practice controls" }).tap();
  await page.getByRole("button", { name: "Show controls" }).tap();
  await page.getByRole("button", { name: "No piano connected" }).tap();
  await expect(
    page.getByRole("heading", { name: "MIDI connection" }),
  ).toBeVisible();
  await expect(page.getByText("Damper · CC64")).toBeVisible();
  await page
    .getByRole("checkbox", { name: "Swipe to turn pages at fit scale" })
    .uncheck();
  await page.getByRole("button", { name: "Save settings" }).tap();
  await page.getByRole("button", { name: "Progress", exact: true }).tap();
  await expect(
    page.getByRole("heading", { name: "Waltz in C-sharp minor" }),
  ).toBeVisible();
  const overflowing = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflowing).toBe(false);
});

test("import private recording when available and preserve original bytes", async ({
  page,
}) => {
  let buffer: Buffer;
  try {
    buffer = readFileSync(new URL("../../1.mid", import.meta.url));
  } catch {
    test.skip(true, "Private MIDI is intentionally not committed");
    return;
  }
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).tap();
  const chooserPromise = page.waitForEvent("filechooser");
  await page
    .getByRole("button", { name: "Import MIDI / CSV", exact: true })
    .tap();
  const chooser = await chooserPromise;
  await chooser.setFiles({ name: "1.mid", mimeType: "audio/midi", buffer });
  await expect(
    page.getByText("Imported successfully. The original file is preserved."),
  ).toBeVisible();
  await page
    .getByRole("button")
    .filter({ has: page.getByRole("heading", { name: /Imported 1/ }) })
    .first()
    .tap();
  const link = page.getByRole("link", { name: "Export original MIDI" });
  await expect(link).toBeVisible();
  const response = await page.request.get((await link.getAttribute("href"))!);
  expect((await response.body()).equals(buffer)).toBe(true);
  await page.getByRole("button", { name: "View MIDI measurements" }).tap();
  await expect(
    page.getByRole("heading", { name: "The shape of your touch" }),
  ).toBeVisible();
  await page.screenshot({ path: "/tmp/chopin-analysis.png", fullPage: true });
});

test("PDF import, touch pages, pinch, pan, saved position and fullscreen", async ({
  page,
  context,
}) => {
  const { scorePdf } = await import("./pdf-fixture");
  // Reset gesture preferences changed by other tests through the public settings API.
  const settings = await (await page.request.get("/api/settings")).json();
  await page.request.put("/api/settings", {
    data: { ...settings, swipe: true, pinch: true, double_tap: true },
  });
  await page.request.put("/api/pieces/n9-1/view", {
    data: { page: 1, zoom: 1, two_pages: false, crop: 0 },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  const volume = page
    .locator(".volume-row")
    .filter({ hasText: "Nocturnes · Volume VII" });
  const promise = page.waitForEvent("filechooser");
  await volume.getByRole("button", { name: /Import PDF|Replace PDF/ }).tap();
  await (
    await promise
  ).setFiles({
    name: "navigation.pdf",
    mimeType: "application/pdf",
    buffer: scorePdf(),
  });
  await expect(
    page.getByText(
      "PDF imported. Set the piece page ranges using its edit button.",
    ),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Filter library" })
    .selectOption("Nocturnes");
  await page
    .getByRole("button", { name: "Edit Nocturne Op. 9 · No. 1", exact: true })
    .tap();
  await page.getByLabel("First PDF page (1-based)").fill("1");
  await page.getByLabel("Last PDF page (inclusive)").fill("3");
  await page.getByRole("button", { name: "Save piece", exact: true }).tap();
  await page
    .locator(".piece-card")
    .filter({ hasText: "Op. 9 · No. 1" })
    .getByRole("button", { name: "Open score", exact: true })
    .tap();
  await expect(
    page.getByLabel("Score PDF page 1", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next page", exact: true }).tap();
  await expect(
    page.getByLabel("Score PDF page 2", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Previous page", exact: true }).tap();
  const stage = page.locator(".score-stage");
  const box = (await stage.boundingBox())!;
  const x = box.x + box.width * 0.65,
    y = box.y + box.height * 0.5;
  const cdp = await context.newCDPSession(page);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x, y }],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ x: x - 130, y }],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await expect(
    page.getByLabel("Score PDF page 2", { exact: true }),
  ).toBeVisible();
  // Two-finger pinch expands score, then one-finger drag pans without turning.
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [
      { id: 1, x: x - 70, y },
      { id: 2, x: x + 70, y },
    ],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [
      { id: 1, x: x - 130, y },
      { id: 2, x: x + 130, y },
    ],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await expect(page.locator(".paper-pair")).not.toHaveCSS(
    "transform",
    "matrix(1, 0, 0, 1, 0, 0)",
  );
  const transform = await page
    .locator(".paper-pair")
    .evaluate((e) => getComputedStyle(e).transform);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x, y }],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ x: x - 100, y: y + 25 }],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await expect(
    page.getByLabel("Score PDF page 2", { exact: true }),
  ).toBeVisible();
  expect(
    await page
      .locator(".paper-pair")
      .evaluate((e) => getComputedStyle(e).transform),
  ).not.toBe(transform);
  await page.getByRole("button", { name: "Fit to page", exact: true }).tap();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Enter fullscreen", exact: true })
    .tap();
  await expect(
    page.getByRole("button", { name: "Exit fullscreen", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Exit fullscreen", exact: true })
    .tap();
  await page.waitForTimeout(650);
  await page.reload();
  await expect(
    page.getByLabel("Score PDF page 2", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await page.screenshot({ path: "/tmp/chopin-practice.png", fullPage: true });
});
