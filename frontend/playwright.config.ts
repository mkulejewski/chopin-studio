import { isolatedApp } from "./playwright.shared";
import { defineConfig } from "@playwright/test";
export default defineConfig({
  outputDir: "./test-results/general",
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    headless: true,
    baseURL: "http://127.0.0.1:8766",
    channel: process.env.PLAYWRIGHT_CHANNEL,
    hasTouch: true,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "full-hd",
      use: { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 },
    },
    {
      name: "landscape-touch",
      use: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 },
    },
    {
      name: "compact-touch",
      use: { viewport: { width: 820, height: 1180 }, deviceScaleFactor: 1.5 },
    },
  ],
  webServer: isolatedApp(8766, "general"),
});
