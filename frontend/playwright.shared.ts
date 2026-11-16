import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

/** Each invocation owns its data/state; never attach to a running application. */
export function isolatedApp(port: number, suite: string) {
  const root = mkdtempSync(join(tmpdir(), `chopin-${suite}-browser-`));
  return {
    command: "../.venv/bin/python -m chopin",
    url: `http://127.0.0.1:${port}/api/status`,
    reuseExistingServer: false,
    env: {
      CHOPIN_DATA_DIR: join(root, "data"),
      CHOPIN_NO_HARDWARE: "1",
      CHOPIN_PORT: String(port),
      XDG_STATE_HOME: join(root, "state"),
    },
  };
}
