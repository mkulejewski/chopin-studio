import { test, expect } from "@playwright/test";
test.use({ timezoneId: "Europe/Warsaw" });

test("daily Learning groups collapse short takes and retain per-take review/export/delete", async ({
  page,
}, info) => {
  const make = (
    id: string,
    started: string,
    extra: Record<string, unknown> = {},
  ) => ({
    id,
    name: `Learning take ${id}`,
    started,
    source: "learning",
    status: "saved",
    duration: 6,
    events: 10,
    error: null,
    learning_piece_id: "e25-1",
    learning_piece_title: "Étude “Aeolian Harp”",
    learning_piece_opus: "25 · No. 1",
    ...extra,
  });
  let sessions = [
    make("first", "2026-11-10T23:30:00Z"),
    make("second", "2026-11-11T10:00:00Z"),
    make("next-day", "2026-11-11T23:05:00Z"),
    make("other", "2026-11-11T08:00:00Z", {
      learning_piece_id: "n9-1",
      learning_piece_title: "Nocturne",
      learning_piece_opus: "9 · No. 1",
    }),
    make("practice", "2026-11-11T12:00:00Z", {
      name: "Ordinary practice",
      source: "live",
      learning_piece_id: null,
    }),
  ];
  const deleted: string[] = [];
  await page.route("**/api/sessions", (route) =>
    route.fulfill({ json: sessions }),
  );
  await page.route(/\/api\/sessions\/[^/]+(?:\/.*)?$/, (route) => {
    const url = new URL(route.request().url());
    const [, id, suffix] = url.pathname.match(
      /\/api\/sessions\/([^/]+)(?:\/(.*))?$/,
    )!;
    if (route.request().method() === "DELETE") {
      deleted.push(id);
      sessions = sessions.filter((s) => s.id !== id);
      return route.fulfill({ json: { ok: true } });
    }
    if (suffix === "summary")
      return route.fulfill({
        json: { notes: 5, markers: [], velocity: [], pedals: [] },
      });
    if (suffix === "recording")
      return route.fulfill({
        json: { microphone: null, timeline_locked: false },
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Sessions", exact: true }).click();
  await expect(page.locator(".session-list > article")).toHaveCount(4);
  await expect(page.locator(".learning-day-session")).toHaveCount(3);
  await expect(page.locator('[data-session-id="first"]')).toHaveCount(0);
  const group = page.locator(
    '[data-learning-group="learning:e25-1:2026-11-11"]',
  );
  await expect(group).toContainText("2 takes");
  await expect(group).toContainText("00:12");
  await group.locator(".learning-day-heading").tap();
  await expect(group.locator(".learning-day-takes > article")).toHaveCount(2);
  await group.locator('[data-session-id="second"] .session-row').click();
  await expect(
    page.getByRole("heading", { name: "Learning take second", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Export original MIDI", exact: true }),
  ).toHaveAttribute("href", "/api/sessions/second/midi");
  await page
    .getByRole("button", { name: "Back to Learning Session", exact: true })
    .click();
  await expect(group.locator(".learning-day-heading")).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  await group
    .locator('[data-session-id="first"]')
    .getByRole("button", { name: "Delete session", exact: true })
    .click();
  const dialog = page.getByRole("alertdialog", {
    name: "Delete this session?",
    exact: true,
  });
  await expect(dialog).toContainText("Learning take first");
  await dialog
    .getByRole("button", { name: "Delete permanently", exact: true })
    .click();
  await expect(group).toContainText("1 take");
  expect(deleted).toEqual(["first"]);
  await expect(group.locator('[data-session-id="second"]')).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Ordinary practice", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("daily-learning-groups.png"),
    fullPage: true,
  });
});
