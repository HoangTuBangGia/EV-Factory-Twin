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
  ? "hosted Supabase Designer/Monitor workflow"
  : `hosted Supabase Designer/Monitor workflow [SKIPPED: missing ${missingCredentials.join(", ")}]`;
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
const revisedCandidateName = `${candidateName}-revision`;
const candidateRobotCount = 3;
const revisionNote = "Move charging away from the main aisle and rerun the benchmark.";

async function login(page: Page, role: RoleName) {
  await page.goto("/login");
  await page.locator("#login-email").fill(credentials[role].email);
  await page.locator("#login-password").fill(credentials[role].password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator(".user-summary")).toContainText(role);
}

async function openScenario(page: Page, name = candidateName) {
  await page.goto("/scenarios");
  const scenarioTab = page.locator(".scenario-tabs button").filter({ hasText: name });
  await expect(scenarioTab).toHaveCount(1);
  await scenarioTab.click();
  await expect(page.locator(".scenario-result")).toContainText(name);
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
    await page.getByText("Advanced settings", { exact: true }).click();
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

  test("Monitor requests a revision with actionable feedback", async ({ page }) => {
    await login(page, "MONITOR");
    await openScenario(page);
    await expect(page.getByRole("button", { name: "Run benchmark" })).toHaveCount(0);
    await page.getByLabel("Revision request").fill(revisionNote);
    await page.getByRole("button", { name: "Request changes" }).click();
    await expect(page.locator(".scenario-status")).toHaveText("REVISION_REQUESTED");
    await expect(page.getByText(revisionNote)).toBeVisible();

    await page.reload();
    await openScenario(page);
    await expect(page.locator(".scenario-status")).toHaveText("REVISION_REQUESTED");
    await expect(page.getByText(revisionNote)).toBeVisible();
  });

  test("Designer runs and submits the linked revision", async ({ page }) => {
    await login(page, "DESIGNER");
    await openScenario(page);
    await expect(page.getByText(revisionNote)).toBeVisible();
    await page.getByRole("button", { name: "Create revised candidate" }).click();

    await expect(page.getByLabel("Scenario name")).toHaveValue(revisedCandidateName);
    await expect(page.getByLabel("Robot count")).toHaveValue(String(candidateRobotCount));
    await page.getByLabel("Robot count").fill(String(candidateRobotCount + 1));
    await page.getByRole("button", { name: "Run benchmark" }).click();

    await expect(page.locator(".scenario-result")).toContainText(revisedCandidateName);
    await expect(page.locator(".scenario-status")).toHaveText("SIMULATED");
    await expect(page.getByText("Revision of")).toBeVisible();
    await page.getByRole("button", { name: "Submit for review" }).click();
    await expect(page.locator(".scenario-status")).toHaveText("SUBMITTED");

    await page.reload();
    await openScenario(page, revisedCandidateName);
    await expect(page.locator(".scenario-status")).toHaveText("SUBMITTED");
  });

  test("Monitor approves and applies the revised candidate", async ({ page }) => {
    await login(page, "MONITOR");
    await openScenario(page, revisedCandidateName);
    await page.getByRole("button", { name: "Approve" }).click();
    await expect(page.locator(".scenario-status")).toHaveText("APPROVED");

    await page.reload();
    await openScenario(page, revisedCandidateName);
    await expect(page.locator(".scenario-status")).toHaveText("APPROVED");
    await page.getByRole("button", { name: "Apply to factory" }).click();
    const confirmation = page.getByRole("dialog", { name: /Apply .* to the factory/ });
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: "Apply to factory" }).click();
    await expect(page.getByRole("status")).toContainText("PENDING");
  });
});
