import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

/**
 * One end-to-end happy path through the real UI and API (brief section 8):
 * register -> create vault -> trustees enrol -> seal -> check in -> force expiry
 * with the demo clock -> trustees decrypt shares -> recover with 2 of 3.
 * Starts a fresh SQLite-backed API (scripts/run_local_server.py) and Vite.
 */
const root = path.resolve(here, "..");
const python =
  process.env.PYTHON ??
  path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");

export const ADMIN_TOKEN = "e2e-admin-token";

export default defineConfig({
  testDir: "e2e",
  timeout: 240_000,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "test-results/e2e-results.json" }]],
  use: { baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure", acceptDownloads: true },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 860 } } }],
  webServer: [
    {
      command: `"${python}" "${path.join(root, "scripts", "run_local_server.py")}" --db e2e.db --fresh --port 8000`,
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DEMO_ADMIN_TOKEN: ADMIN_TOKEN,
        CRON_SECRET: "e2e-cron-secret",
        APP_BASE_URL: "http://127.0.0.1:5173",
        DEMO_MODE: "true",
        EMAIL_MODE: "log",
      },
    },
    {
      command: "npx vite --port 5173 --strictPort --host 127.0.0.1",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
