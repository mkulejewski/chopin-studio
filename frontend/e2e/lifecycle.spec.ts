import { expect, test } from "@playwright/test";

test("an open frontend sends presence with its recurring status polls", async ({ page }) => {
  const heartbeat = () => page.waitForRequest((request) =>
    request.url().endsWith("/api/status") &&
    request.headers()["x-chopin-frontend"] === "1",
  );
  const first = heartbeat();
  await page.goto("/");
  expect((await first).method()).toBe("GET");
  expect((await heartbeat()).method()).toBe("GET");
});

test("a backend stop refreshes the frontend session list", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Record session", exact: true })).toBeEnabled();
  const started = await request.post("/api/record/start");
  const { id } = await started.json();
  await expect(page.getByText("Session recording", { exact: true })).toBeVisible();
  const refreshed = page.waitForResponse(async (response) =>
    response.url().endsWith("/api/sessions") && response.ok() &&
    (await response.json()).some((session: { id: string; status: string }) =>
      session.id === id && session.status === "saved"),
  );
  // Reproduce the externally stopped session observed after disconnection.
  expect((await request.post("/api/record/stop")).ok()).toBeTruthy();
  await refreshed;
  await expect(page.getByRole("button", { name: "Record session", exact: true })).toBeEnabled();
});
