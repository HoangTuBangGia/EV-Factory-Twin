import { expect, type Page, test } from "@playwright/test";

type RoleName = "DESIGNER" | "MONITOR";

interface Credentials {
  email: string;
  password: string;
}

const requiredCredentialNames = [
  "DESIGNER_EMAIL",
  "DESIGNER_PASSWORD",
  "MONITOR_EMAIL",
  "MONITOR_PASSWORD",
] as const;
const missingCredentials = requiredCredentialNames.filter((name) => !process.env[name]?.trim());
const hostedSuiteTitle = missingCredentials.length === 0
  ? "hosted GCP Designer/Monitor workflow"
  : `hosted GCP Designer/Monitor workflow [SKIPPED: missing ${missingCredentials.join(", ")}]`;
const credentials: Record<RoleName, Credentials> = {
  DESIGNER: {
    email: process.env.DESIGNER_EMAIL ?? "",
    password: process.env.DESIGNER_PASSWORD ?? "",
  },
  MONITOR: {
    email: process.env.MONITOR_EMAIL ?? "",
    password: process.env.MONITOR_PASSWORD ?? "",
  },
};
const candidateName = `e2e-rbac-${Date.now()}-${process.pid}`;
const candidateRobotCount = 3;

async function login(page: Page, role: RoleName) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(credentials[role].email);
  await page.getByLabel("Password").fill(credentials[role].password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator(".user-summary")).toContainText(role);
}

async function openScenario(page: Page) {
  await page.goto("/scenarios");
  const scenarioTab = page.locator(".scenario-tabs button").filter({ hasText: candidateName });
  await expect(scenarioTab).toHaveCount(1);
  await scenarioTab.click();
  await expect(page.locator(".scenario-result")).toContainText(candidateName);
}

test.describe(hostedSuiteTitle, () => {
  test.describe.configure({ mode: "serial" });
  test.skip(
    missingCredentials.length > 0,
    `Hosted RBAC E2E skipped; missing environment variables: ${missingCredentials.join(", ")}`,
  );

  test("Designer logs in, runs and recovers a scenario without review controls", async ({ page }) => {
    await login(page, "DESIGNER");
    await expect(page).toHaveURL(/\/scenarios$/);

    await page.getByLabel("Scenario name").fill(candidateName);
    await page.getByLabel("Robot count").fill(String(candidateRobotCount));
    await page.getByLabel("Number of tasks").fill("30");
    await page.getByLabel("Task arrival interval (s)").fill("3");
    await page.getByLabel("Travel time (s)").fill("8");
    await page.getByLabel("Loading time (s)").fill("2");
    await page.getByLabel("Simulation time (s)").fill("120");
    await page.getByRole("button", { name: "Run benchmark" }).click();

    await expect(page.locator(".scenario-result")).toContainText(candidateName);
    await expect(page.locator(".scenario-status")).toHaveText("SIMULATED");
    await page.getByRole("button", { name: "Submit for review" }).click();
    await expect(page.locator(".scenario-status")).toHaveText("SUBMITTED");
    await expect(page.getByText(/Waiting for monitor review/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Reject" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Apply to factory" })).toHaveCount(0);

    await page.reload();
    await openScenario(page);
    await expect(page.locator(".scenario-status")).toHaveText("SUBMITTED");
  });

  test("Monitor cannot run scenarios, then approves and applies the candidate", async ({ page }) => {
    await login(page, "MONITOR");
    await openScenario(page);
    await expect(page.getByRole("button", { name: "Run benchmark" })).toHaveCount(0);
    await page.getByRole("button", { name: "Approve" }).click();
    await expect(page.locator(".scenario-status")).toHaveText("APPROVED");

    await page.reload();
    await openScenario(page);
    await expect(page.locator(".scenario-status")).toHaveText("APPROVED");
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Apply to factory" }).click();
    await expect(page.getByRole("status")).toContainText("PENDING");
  });
});
