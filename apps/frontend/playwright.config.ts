import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const repositoryRoot = path.resolve(__dirname, "../..");
const frontendRoot = path.resolve(__dirname);
const localFrontendUrl = "http://127.0.0.1:3000";
const localBackendUrl = "http://127.0.0.1:8000";
const useExternalServers = process.env.E2E_EXTERNAL_SERVERS === "true";
const baseURL = useExternalServers
  ? process.env.E2E_BASE_URL ?? localFrontendUrl
  : localFrontendUrl;
const backendURL = useExternalServers
  ? process.env.E2E_API_URL ?? localBackendUrl
  : localBackendUrl;
const websocketURL = backendURL.replace(/^http/, "ws") + "/ws/factory";

function definedEnvironment(values: Record<string, string | undefined>) {
  return Object.fromEntries(
    Object.entries(values).filter((entry): entry is [string, string] => entry[1] !== undefined),
  );
}

// Do not forward the test runner's role passwords or backend database URL to
// the Next.js process. Each child receives only the settings it actually uses.
const toolEnvironment = definedEnvironment({
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  USERPROFILE: process.env.USERPROFILE,
  SYSTEMROOT: process.env.SYSTEMROOT,
  TMPDIR: process.env.TMPDIR,
  TEMP: process.env.TEMP,
  TMP: process.env.TMP,
  CI: process.env.CI,
  UV_CACHE_DIR: process.env.UV_CACHE_DIR,
});

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["line"]] : [["list"]],
  use: {
    baseURL,
    // Hosted login sends real demo passwords and receives access/refresh
    // tokens. Playwright traces and network artifacts can capture those
    // secrets, so this suite deliberately retains no browser artifacts.
    trace: "off",
    screenshot: "off",
    video: "off",
    launchOptions: {
      args: [
        "--use-gl=angle",
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
      ],
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: useExternalServers ? undefined : [
    {
      name: "FastAPI",
      command: "uv run --package ev-twin-api uvicorn ev_twin_api.main:app --app-dir apps/backend/src --host 127.0.0.1 --port 8000",
      cwd: repositoryRoot,
      url: `${localBackendUrl}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
      env: definedEnvironment({
        ...toolEnvironment,
        APP_ENV: "e2e",
        CORS_ORIGINS: localFrontendUrl,
        MOCK_FACTORY_ENABLED: "true",
        DATABASE_URL: process.env.DATABASE_URL,
        DATABASE_SSL_MODE: process.env.DATABASE_SSL_MODE,
        AUTH_JWT_SECRET: process.env.AUTH_JWT_SECRET,
      }),
    },
    {
      name: "Next.js",
      command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
      cwd: frontendRoot,
      url: localFrontendUrl,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
      env: definedEnvironment({
        ...toolEnvironment,
        NEXT_PUBLIC_DATA_SOURCE: "api",
        NEXT_PUBLIC_API_URL: localBackendUrl,
        NEXT_PUBLIC_WS_URL: websocketURL,
      }),
    },
  ],
});
