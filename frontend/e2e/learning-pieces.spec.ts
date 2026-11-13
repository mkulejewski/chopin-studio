import { test, expect } from "@playwright/test";
import { scorePdf } from "./pdf-fixture";
const base = "/api/learning/p53";
test.afterEach(async ({ request }) => {
  await request.post("/api/learning/selection", {
    data: { piece_id: "e25-1" },
  });
});
test("Library links open the matching Learning lesson", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).click();
  const catalogue = await (await page.request.get("/api/learning")).json();
  const library = await (await page.request.get("/api/library")).json();
  const lessonIds = catalogue.pieces.map(
    (piece: { piece_id: string }) => piece.piece_id,
  );
  await expect(
    page.getByRole("button", { name: "Open in Learning", exact: true }),
  ).toHaveCount(lessonIds.length);
  for (const piece of library.pieces) {
    await expect(
      page.locator(`[data-piece-id="${piece.id}"]`).getByRole("button", {
        name: "Open in Learning",
        exact: true,
      }),
    ).toHaveCount(lessonIds.includes(piece.id) ? 1 : 0);
  }
  // Both directions must override the previously selected lesson.
  for (const pieceId of ["p53", "e25-1"]) {
    const card = page.locator(`[data-piece-id="${pieceId}"]`);
    const button = card.getByRole("button", {
      name: "Open in Learning",
      exact: true,
    });
    await button.scrollIntoViewIfNeeded();
    const bounds = await button.boundingBox();
    const cardBounds = await card.boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(cardBounds!.x);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
      cardBounds!.x + cardBounds!.width,
    );
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
      page.viewportSize()!.width,
    );
    await button.click();
    await expect(
      page.getByRole("combobox", { name: "Learning piece", exact: true }),
    ).toHaveValue(pieceId);
    expect(
      (await (await page.request.get("/api/learning")).json()).selected_piece,
    ).toBe(pieceId);
    expect(
      (await (await page.request.get("/api/status")).json()).active,
    ).toBeNull();
    await page.getByRole("button", { name: "Library", exact: true }).click();
  }
});

test("a failed Library lesson selection keeps Library open", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).click();
  await page.route("**/api/learning/selection", (route) =>
    route.fulfill({
      status: 409,
      json: { detail: "Lesson selection unavailable" },
    }),
  );
  await page
    .locator('[data-piece-id="p53"]')
    .getByRole("button", {
      name: "Open in Learning",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("Lesson selection unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Your score library." }),
  ).toBeVisible();
  await expect(
    page.locator('[data-piece-id="p53"]').getByRole("button", {
      name: "Open in Learning",
      exact: true,
    }),
  ).toBeEnabled();
});

test("Heroic restores its separate routine, hand and startup selection", async ({
  page,
}) => {
  await page.request.post("/api/learning/selection", {
    data: { piece_id: "e25-1" },
  });
  const aeolian = await (await page.request.get("/api/learning/e25-1")).json();
  await page.request.put("/api/learning/e25-1", {
    data: { config: { ...aeolian.profile.config, visible: 2 } },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Learning piece", exact: true })
    .selectOption("p53");
  await expect(
    page.getByText("Heroic Polonaise · Op. 53", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Proposed section progression", { exact: true }),
  ).toBeVisible();
  expect((await (await page.request.get(base)).json()).automatic_ready).toBe(
    true,
  );
  await page
    .getByRole("combobox", { name: "Practice hands", exact: true })
    .selectOption("left");
  const heroic = await (await page.request.get(base)).json();
  await page.request.put(base, {
    data: { config: { ...heroic.profile.config, visible: 4 } },
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Learning", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Learning piece", exact: true }),
  ).toHaveValue("p53");
  await expect(
    page.getByRole("combobox", { name: "Practice hands", exact: true }),
  ).toHaveValue("left");
  await page
    .getByRole("button", { name: "Edit routine & chunks", exact: true })
    .click();
  await expect(
    page.getByRole("spinbutton", { name: "Visible repetitions", exact: true }),
  ).toHaveValue("4");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Learning piece", exact: true })
    .selectOption("e25-1");
  await page
    .getByRole("button", { name: "Edit routine & chunks", exact: true })
    .click();
  await expect(
    page.getByRole("spinbutton", { name: "Visible repetitions", exact: true }),
  ).toHaveValue("2");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Learning piece", exact: true })
    .selectOption("p53");
  await expect(
    page.getByRole("combobox", { name: "Practice hands", exact: true }),
  ).toHaveValue("left");
});
test("Heroic scan layout and score fullscreen keep controls within the viewport", async ({
  page,
}) => {
  await page.request.post("/api/learning/selection", {
    data: { piece_id: "p53" },
  });
  await page.request.post("/api/volumes/polonaises/pdf", {
    multipart: {
      file: {
        name: "synthetic-polonaises.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(73, true),
      },
    },
  });
  // Only the UI readiness flag is mocked for this original synthetic PDF.
  // The backend hash gate remains intact; no test take is started.
  await page.route("**/api/learning/p53", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({
      response,
      json: {
        ...data,
        ready: true,
        source_notice: "Synthetic layout fixture; no edition approval",
      },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await expect(page.locator(".learning canvas").first()).toBeVisible();
  const picker = await page
    .getByRole("combobox", { name: "Learning piece", exact: true })
    .boundingBox();
  expect(picker!.x + picker!.width).toBeLessThanOrEqual(
    page.viewportSize()!.width,
  );
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => document.fullscreenElement?.className))
    .toContain("learning-workspace");
  const controls = page.getByRole("complementary", {
    name: "Learning controls",
    exact: true,
  });
  await expect(
    controls.getByRole("button", { name: "Start attempt", exact: true }),
  ).toBeVisible();
  await expect(
    controls.getByText("Study with the score", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".learning .score-render-status"),
  ).not.toBeVisible();
  const bounds = await controls.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
    page.viewportSize()!.width + 1,
  );
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(
    page.viewportSize()!.height + 1,
  );
  await page.screenshot({
    path: test.info().outputPath("heroic-fullscreen.png"),
  });
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .click();
  expect((await page.request.post(base + "/start")).status()).toBe(400);
});
