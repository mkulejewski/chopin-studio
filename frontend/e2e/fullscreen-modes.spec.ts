import { test, expect } from "@playwright/test";
import { scorePdf } from "./pdf-fixture";

test("app fullscreen and score fullscreen have distinct controls", async ({
  page,
}) => {
  await page.request.post("/api/volumes/nocturnes/pdf", {
    multipart: {
      file: {
        name: "fullscreen.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(3, true),
      },
    },
  });
  const library = await (await page.request.get("/api/library")).json();
  const piece = library.pieces.find((p: any) => p.id === "n9-1");
  await page.request.put("/api/pieces/n9-1", {
    data: { ...piece, start_page: 1, end_page: 3 },
  });
  await page.request.put("/api/pieces/n9-1/view", {
    data: { page: 1, zoom: 1, two_pages: true, crop: 0 },
  });
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("fullscreen-fixture-opened")) {
      localStorage.setItem("chopin-piece", "n9-1");
      sessionStorage.setItem("fullscreen-fixture-opened", "1");
    }
  });
  await page.goto("/");
  await expect(
    page.getByLabel("Score PDF page 1", { exact: true }),
  ).toBeVisible();
  const app = page.getByRole("button", {
    name: "Enter app fullscreen",
    exact: true,
  });
  const score = page.getByRole("button", {
    name: "Enter score fullscreen",
    exact: true,
  });
  await expect(app).toHaveText("App fullscreen");
  await expect(score).toHaveText("Score fullscreen");
  await expect(
    page.getByRole("button", { name: "Fit to page", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next page", exact: true }).tap();
  await expect(
    page.getByLabel("Score PDF page 2", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "First score page", exact: true })
    .tap();
  await expect(
    page.getByLabel("Score PDF page 1", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "First score page", exact: true }),
  ).toBeDisabled();
  for (let attempt = 0; attempt < 2; attempt++) {
    await app.tap();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.fullscreenElement === document.documentElement,
        ),
      )
      .toBe(true);
    await expect(page.locator(".sidebar")).toBeVisible();
    await expect(page.locator(".app")).not.toHaveClass(/distraction-free/);
    await expect(page.locator(".live-overlay")).toHaveCount(0);
    await page
      .getByRole("button", { name: "Exit app fullscreen", exact: true })
      .tap();
  }
  await app.tap();
  await score.tap();
  await expect
    .poll(() => page.evaluate(() => document.fullscreenElement?.className))
    .toBe("score-shell");
  await expect(
    page.getByRole("button", { name: "Fit to page", exact: true }),
  ).toBeVisible();
  const fullscreenRecorder = page.locator(".score-shell").getByRole("button", {
    name: "Record session",
    exact: true,
  });
  await fullscreenRecorder.tap();
  await expect
    .poll(
      async () => (await (await page.request.get("/api/status")).json()).active,
    )
    .toBeTruthy();
  const fullscreenStop = page.locator(".score-shell").getByRole("button", {
    name: "Stop session",
    exact: true,
  });
  await fullscreenStop.tap();
  const stopDialog = page
    .locator(".score-shell")
    .getByRole("dialog", { name: "Stop session", exact: true });
  await expect(stopDialog).toBeVisible();
  await stopDialog
    .getByRole("button", { name: "Keep recording", exact: true })
    .tap();
  await expect(fullscreenStop).toBeVisible();
  // Keep the remaining navigation assertions in Practice; test stop-and-save
  // after them because saving navigates to Sessions.
  await page
    .getByRole("button", { name: "Show recognition", exact: true })
    .tap();
  await expect(page.locator(".score-shell .live-overlay")).toBeVisible();
  await expect(
    page
      .locator(".score-shell .live-overlay")
      .getByRole("button", { name: "Live controls", exact: true }),
  ).toBeVisible();
  const auto = page.getByRole("button", {
    name: "Automatic page turns",
    exact: true,
  });
  const before = await auto.getAttribute("aria-pressed");
  await auto.tap();
  await expect(auto).toHaveAttribute(
    "aria-pressed",
    before === "true" ? "false" : "true",
  );
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/settings")).json()).live_auto_turn,
    )
    .toBe(before !== "true");
  // Loading/error notices must not consume the score's flex height. Exercise
  // the same DOM insertion/removal as rendering state, independent of PDF speed.
  const heights = await page.evaluate(async () => {
    const shell = document.querySelector<HTMLDivElement>(".score-shell")!;
    const stage = shell.querySelector<HTMLDivElement>(".score-stage")!;
    const status = document.createElement("div");
    status.className = "score-render-status";
    status.setAttribute("role", "status");
    status.textContent = "Preparing page 1–2…";
    const before = stage.getBoundingClientRect().height;
    const samples = [];
    for (let i = 0; i < 3; i++) {
      shell.append(status);
      samples.push(stage.getBoundingClientRect().height);
      await new Promise((resolve) => requestAnimationFrame(resolve));
      status.remove();
      samples.push(stage.getBoundingClientRect().height);
    }
    return { before, samples };
  });
  for (const height of heights.samples)
    expect(height).toBeCloseTo(heights.before, 0);
  await expect(page.locator(".score-render-status")).toHaveCount(0);
  // The asynchronous resize/render cycle should settle and stay settled.
  await page.waitForTimeout(800);
  await expect(page.locator(".score-render-status")).toHaveCount(0);
  await page.screenshot({
    path: `/tmp/chopin-score-fullscreen-${test.info().project.name}.png`,
  });
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .tap();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.fullscreenElement === document.documentElement,
      ),
    )
    .toBe(true);
  await expect(page.locator(".sidebar")).toBeVisible();
  await page
    .getByRole("button", { name: "Exit app fullscreen", exact: true })
    .tap();
  await expect(app).toBeVisible();
  // Enter score fullscreen directly as well as from app fullscreen.
  await score.tap();
  await expect
    .poll(() => page.evaluate(() => document.fullscreenElement?.className))
    .toBe("score-shell");
  await page.getByRole("button", { name: "Clear score", exact: true }).tap();
  await expect(page.locator(".paper-pair canvas")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Let the music begin." }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => localStorage.getItem("chopin-piece")),
  ).toBeNull();
  expect(
    (await page.request.get("/api/volumes/nocturnes/pdf")).ok(),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .tap();
  await expect(app).toBeVisible();
  await score.tap();
  await fullscreenStop.tap();
  await stopDialog
    .getByRole("button", { name: "Stop & save session", exact: true })
    .tap();
  await expect
    .poll(
      async () => (await (await page.request.get("/api/status")).json()).active,
    )
    .toBeFalsy();
  await page.getByRole("button", { name: "Practice", exact: true }).tap();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Let the music begin." }),
  ).toBeVisible();
});
