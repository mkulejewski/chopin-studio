import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["learning.spec.ts", "fullscreen-modes.spec.ts"],
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8767",
    channel: "chrome",
    hasTouch: true,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "landscape", use: { viewport: { width: 1280, height: 900 } } },
    { name: "compact", use: { viewport: { width: 820, height: 1180 } } },
  ],
  webServer: {
    command: "../.venv/bin/python -m chopin",
    url: "http://127.0.0.1:8767/api/status",
    reuseExistingServer: true,
    env: {
      CHOPIN_DATA_DIR: "/tmp/chopin-learning-browser",
      CHOPIN_NO_HARDWARE: "1",
      CHOPIN_PORT: "8767",
    },
  },
});
