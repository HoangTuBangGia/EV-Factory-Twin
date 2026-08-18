import { chromium } from "playwright-core";

const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-sandbox"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
// Offline box: an unreachable webfont makes screenshot() hang on "waiting for fonts".
await page.route("**/*", (route) => {
  const u = route.request().url();
  if (/fonts\.(googleapis|gstatic)\.com|\.woff2?($|\?)/.test(u)) return route.abort();
  return route.continue();
});
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 180000 });
await page.waitForSelector("canvas, .robot-marker", { timeout: 180000 }).catch(() => undefined);
await page.waitForTimeout(Number(process.argv[4] ?? 9000));
const info = await page.evaluate(() => ({
  view: document.querySelector("[data-view]")?.getAttribute("data-view") ?? null,
  canvases: document.querySelectorAll("canvas").length,
  markers: document.querySelectorAll(".robot-marker").length,
  text: document.body.innerText.slice(0, 600),
}));
console.log(JSON.stringify({ info, errors: errors.slice(0, 12) }, null, 2));
await page.screenshot({ path: out, timeout: 120000, animations: "disabled" });
console.log(`wrote ${out}`);
await browser.close();
