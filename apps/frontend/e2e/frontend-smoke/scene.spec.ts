import { expect, test } from "@playwright/test";

test("renders the fixture-backed 3D factory scene without browser errors", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  await page.goto("/scene-probe", { waitUntil: "domcontentloaded" });

  const canvas = page.locator("canvas");
  await expect(canvas).toHaveCount(1);
  await expect(canvas).toBeVisible();
  const canvasBox = await canvas.boundingBox();
  const viewport = page.viewportSize();
  expect(canvasBox?.width).toBeLessThanOrEqual(viewport?.width ?? 0);
  expect(canvasBox?.height).toBeLessThanOrEqual(viewport?.height ?? 0);
  await expect(page.getByTestId("scene-probe")).toHaveAttribute("data-robot-count", "5");
  await expect.poll(() => canvas.evaluate((element) => {
    const renderedCanvas = element as HTMLCanvasElement;
    const context = renderedCanvas.getContext("webgl2") ?? renderedCanvas.getContext("webgl");
    return Boolean(
      context
      && !context.isContextLost()
      && renderedCanvas.width > 0
      && renderedCanvas.height > 0
    );
  })).toBe(true);
  await expect.poll(() => browserErrors).toEqual([]);
});
