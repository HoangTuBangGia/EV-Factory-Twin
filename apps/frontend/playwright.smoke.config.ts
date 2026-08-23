import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const frontendRoot = path.resolve(__dirname);
const localURL = "http://127.0.0.1:3100";
const useExternalServer = process.env.SMOKE_EXTERNAL_SERVER === "true";

function definedEnvironment(values: Record<string, string | undefined>) {
  return Object.fromEntries(
    Object.entries(values).filter((entry): entry is [string, string] => entry[1] !== undefined),
  );
}

const toolEnvironment = definedEnvironment({
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  USERPROFILE: process.env.USERPROFILE,
  SYSTEMROOT: process.env.SYSTEMROOT,
  TMPDIR: process.env.TMPDIR,
  TEMP: process.env.TEMP,
  TMP: process.env.TMP,
  CI: process.env.CI,
});

export default defineConfig({
  testDir: "./e2e/frontend-smoke",
  outputDir: "./test-results/frontend-smoke",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["line"]] : [["list"]],
  use: {
    baseURL: useExternalServer ? process.env.SMOKE_BASE_URL ?? localURL : localURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
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
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
  webServer: useExternalServer ? undefined : {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
    cwd: frontendRoot,
    url: `${localURL}/scene-probe`,
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    env: definedEnvironment({
      ...toolEnvironment,
      NEXT_PUBLIC_DATA_SOURCE: "mock",
    }),
  },
});
