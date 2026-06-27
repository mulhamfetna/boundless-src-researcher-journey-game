// Real-browser regression test for the order-question drag-and-drop.
// jsdom has no layout/hit-testing, so this drives system Chrome via puppeteer-core.
// Skips (exit 0) when no Chrome binary is available, so it never blocks environments
// without a browser. Run directly: `node frontend/tests/drag.e2e.mjs`.
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = dirname(fileURLToPath(import.meta.url));
const FE = join(dir, "..");

function findChrome() {
  const candidates = [
    process.env.PUPPETEER_EXECUTABLE_PATH,
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean);
  return candidates.find((p) => existsSync(p));
}

const chrome = findChrome();
if (!chrome) {
  console.log("SKIP drag.e2e: no Chrome binary found (set PUPPETEER_EXECUTABLE_PATH to enable).");
  process.exit(0);
}

const { default: puppeteer } = await import("puppeteer-core");

const css = readFileSync(join(FE, "styles.css"), "utf8");
const appjs = readFileSync(join(FE, "app.js"), "utf8").replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
const mainHtml = readFileSync(join(FE, "index.html"), "utf8").match(/<main[\s\S]*<\/main>/)[0];

const html = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>${css}</style>
<script>window.Telegram={WebApp:{initData:"",ready(){},expand(){}}};window.fetch=()=>Promise.resolve({ok:true,json:async()=>[]});</script>
</head><body>${mainHtml}
<script>${appjs}</script>
<script>
  window.__lost = 0;
  document.addEventListener('lostpointercapture', e => { if (e.target.closest && e.target.closest('.order-row')) window.__lost++; }, true);
  document.getElementById('screen-runner').classList.remove('hidden');
  renderOrder({ id:1, type:'order', prompt_ar:'رتب', concept:'c', items_ar:['A','B','C','D'], correct_sequence:[0,1,2,3] });
</script></body></html>`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const readOrder = (page) => page.$$eval(".order-row", (rows) => rows.map((r) => r.dataset.orig).join(""));

let failed = false;
function check(name, cond) {
  console.log(`${cond ? "✓" : "✗"} ${name}`);
  if (!cond) failed = true;
}

const browser = await puppeteer.launch({
  executablePath: chrome, headless: "new", args: ["--no-sandbox", "--disable-setuid-sandbox"],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 800, hasTouch: true, isMobile: true });
  await page.setContent(html, { waitUntil: "load" });
  await sleep(60);

  const before = await readOrder(page);
  const boxes = await page.$$eval(".order-row", (rows) =>
    rows.map((r) => { const b = r.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2, h: b.height }; }));
  const start = boxes[0];
  const targetY = boxes[boxes.length - 1].y + boxes[boxes.length - 1].h + 20;

  // drag the first row down past the last row
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await sleep(20);
  for (let y = start.y; y <= targetY; y += 6) { await page.mouse.move(start.x, y); await sleep(16); }
  await page.mouse.up();
  await sleep(60);

  const after = await readOrder(page);
  const lost = await page.evaluate(() => window.__lost);

  check("dragging the first row reorders the list", before !== after);
  check("the dragged row ends up last", after.endsWith(before[0]));
  check("pointer capture is not lost mid-drag (no lostpointercapture)", lost === 0);

  await page.close();
} finally {
  await browser.close();
}

if (failed) { console.error("drag.e2e FAILED"); process.exit(1); }
console.log("drag.e2e passed");
