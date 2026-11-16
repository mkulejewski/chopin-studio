import { isolatedApp } from "./playwright.shared";
import { defineConfig } from "@playwright/test";
export default defineConfig({
  outputDir: "./test-results/sessions",
  testDir: "./e2e",
  testMatch: [
    "session-groups.spec.ts",
    "recording-cleanup.spec.ts",
    "piece-sessions.spec.ts",
    "analysis-evidence.spec.ts",
    "passage-analysis.spec.ts",
    "recordings-library.spec.ts",
  ],
  workers: 1,
  timeout: 30000,
  use: {
    headless: true,
    baseURL: "http://127.0.0.1:8768",
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
    hasTouch: true,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "full-hd", use: { viewport: { width: 1920, height: 1080 } } },
    { name: "landscape", use: { viewport: { width: 1280, height: 900 } } },
    { name: "compact", use: { viewport: { width: 820, height: 1180 } } },
  ],
  webServer: isolatedApp(8768, "sessions"),
});
