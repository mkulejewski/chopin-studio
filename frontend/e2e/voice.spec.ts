import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const w = window as any;
    w.SpeechRecognition = class {
      onresult?: (event: any) => void;
      onend?: () => void;
      onspeechend?: () => void;
      onspeechstart?: () => void;
      onerror?: (event: any) => void;
      start() {
        w.voiceRecognition = this;
      }
      stop() {
        w.voiceStops = (w.voiceStops || 0) + 1;
        this.onend?.();
      }
      abort() {
        w.voiceAborts = (w.voiceAborts || 0) + 1;
      }
    };
  });
});

test("touch voice command waits for speech end then opens the matching score once", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await expect(page.locator(".piece-card").first()).toBeVisible();
  await page.getByRole("button", { name: "Voice command", exact: true }).tap();
  await expect(
    page.getByRole("button", { name: "Cancel voice command" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.evaluate(() => {
    const r = (window as any).voiceRecognition;
    r.onresult({
      results: [{ isFinal: false, 0: { transcript: "open Nocturne" } }],
    });
  });
  await expect(page.locator("#voice-feedback")).toContainText("open Nocturne");
  await expect(page.locator(".breadcrumb")).toContainText("Library");
  await page.evaluate(() => {
    const r = (window as any).voiceRecognition;
    r.onresult({
      results: [
        {
          isFinal: true,
          0: { transcript: "open Nocturne Opus Nine Number One" },
        },
      ],
    });
    r.onspeechend();
  });
  await expect(page.locator("#voice-feedback")).toContainText(
    "Opened Nocturne Op. 9",
  );
  await expect(page.locator(".breadcrumb")).toContainText("Practice");
  expect(await page.evaluate(() => localStorage.getItem("chopin-piece"))).toBe(
    "n9-1",
  );
  expect(await page.evaluate(() => (window as any).voiceStops)).toBe(1);
  await expect(
    page.getByRole("button", { name: "Voice command", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  await page.screenshot({ path: "/tmp/chopin-voice-control.png" });
});

test("voice cancellation, denied permission and unsupported browsers are recoverable", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Voice command", exact: true }).tap();
  await page.getByRole("button", { name: "Cancel voice command" }).tap();
  await expect(page.locator("#voice-feedback")).toContainText("cancelled");
  await page.getByRole("button", { name: "Voice command", exact: true }).tap();
  await page.evaluate(() =>
    (window as any).voiceRecognition.onerror({ error: "not-allowed" }),
  );
  await expect(page.locator("#voice-feedback")).toContainText(
    "permission was denied",
  );
  await page.evaluate(() => {
    (window as any).SpeechRecognition = undefined;
    (window as any).webkitSpeechRecognition = undefined;
  });
  // Force a render after changing browser capabilities.
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await page.getByRole("button", { name: "Voice command", exact: true }).tap();
  await expect(page.locator("#voice-feedback")).toContainText(
    "unavailable in this browser",
  );
});

test("ambiguous commands leave the current piece unchanged", async ({
  page,
}) => {
  await page.goto("/");
  const before = await page.evaluate(() =>
    localStorage.getItem("chopin-piece"),
  );
  await page.getByRole("button", { name: "Library", exact: true }).tap();
  await expect(page.locator(".piece-card").first()).toBeVisible();
  await page.getByRole("button", { name: "Voice command", exact: true }).tap();
  await page.evaluate(() => {
    const r = (window as any).voiceRecognition;
    r.onresult({
      results: [{ isFinal: true, 0: { transcript: "open nocturne" } }],
    });
    r.onend();
  });
  await expect(page.locator("#voice-feedback")).toContainText("matches");
  expect(await page.evaluate(() => localStorage.getItem("chopin-piece"))).toBe(
    before,
  );
});
