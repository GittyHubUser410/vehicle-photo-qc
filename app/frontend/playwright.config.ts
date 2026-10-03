import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:8000",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `"${process.env.QC_TEST_PYTHON || "python"}" scripts/test_server.py`,
    cwd: "../..",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
