import { defineConfig } from "@playwright/test";
export default defineConfig({
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
      name: "landscape-touch",
      use: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 },
    },
    {
      name: "compact-touch",
      use: { viewport: { width: 820, height: 1180 }, deviceScaleFactor: 1.5 },
    },
  ],
  webServer: {
    command: "../.venv/bin/python -m chopin",
    url: "http://127.0.0.1:8766/api/status",
    reuseExistingServer: false,
    env: {
      CHOPIN_DATA_DIR: process.env.CHOPIN_TEST_DATA || "/tmp/chopin-e2e-data",
      CHOPIN_NO_HARDWARE: "1",
      CHOPIN_PORT: "8766",
      XDG_STATE_HOME: process.env.CHOPIN_TEST_STATE || "/tmp/chopin-e2e-state",
    },
  },
});
