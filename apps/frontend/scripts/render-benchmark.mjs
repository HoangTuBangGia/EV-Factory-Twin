import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.BENCHMARK_BASE_URL ?? "http://127.0.0.1:3000";
const durationMs = Number(process.env.BENCHMARK_DURATION_MS ?? 5000);
if (!Number.isFinite(durationMs) || durationMs < 1000) {
  throw new Error("BENCHMARK_DURATION_MS must be at least 1000");
}

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(`${baseUrl}/scene-probe`, { waitUntil: "networkidle" });
  await page.locator("canvas").waitFor({ state: "visible" });
  const report = await page.evaluate(async (measurementMs) => {
    const frameTimes = [];
    await new Promise((resolve) => {
      const started = performance.now();
      let previous = started;
      function frame(now) {
        frameTimes.push(now - previous);
        previous = now;
        if (now - started >= measurementMs) resolve();
        else requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });
    const sorted = [...frameTimes].sort((left, right) => left - right);
    const percentile = (value) => sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * value))];
    const elapsed = frameTimes.reduce((total, value) => total + value, 0);
    return {
      duration_ms: elapsed,
      frames: frameTimes.length,
      average_fps: frameTimes.length / (elapsed / 1000),
      frame_time_p95_ms: percentile(0.95),
      dropped_frame_percent: frameTimes.filter((value) => value > 1000 / 30).length / frameTimes.length * 100,
    };
  }, durationMs);
  const output = path.resolve("../../evaluation/reports/render_performance.json");
  await mkdir(path.dirname(output), { recursive: true });
  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} finally {
  await browser.close();
}
