/**
 * Render the launch slides from HTML instead of prompting an image model.
 *
 * Why this exists: the whole risk in docs/launch/poster-prompts.md is that image
 * models render Arabic by imitating letter shapes rather than spelling — correct
 * letterforms, meaningless words. Every mitigation in that document (text-free
 * variants, reserved zones, read-every-word-aloud checklists) works around that
 * one failure.
 *
 * HTML does not have that failure. The text is the text. It also gives exact
 * alignment across nine slides, real embedded fonts, and version control over
 * the wording — a typo becomes a one-line fix and a re-run rather than another
 * spin of the generation lottery.
 *
 * Station content lives HERE, in one array, so the carousel slides and the
 * single all-stations poster can never drift apart.
 *
 *   node scripts/posters/build.mjs            # HTML + PNGs
 *   node scripts/posters/build.mjs --html     # HTML only (open it in a browser)
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const require = createRequire(join(REPO, "frontend", "package.json"));

const SRC = join(REPO, "docs", "launch", "posters", "carousel.src.html");
const OUT_HTML = join(REPO, "docs", "launch", "posters", "carousel.html");
const OUT_PNG = join(REPO, "docs", "launch", "assets", "carousel");
const FONTS = join(REPO, "frontend", "fonts");

/**
 * The seven stations. `what` is the skill; `example` is a real task drawn from
 * the question bank — the proof of "practice, not recall", and the line that
 * does the actual persuading.
 */
const STATIONS = [
  {
    title: "تصنيف المجلات العلمية",
    what: "فحص رصانة المجلة وتصنيفها، وكشف المؤشّرات التي تدلّ على مجلة مفترسة قبل الإرسال.",
    example: "أمامك دعوة نشر وصلت إلى بريدك — حدِّد كل العلامات الحمراء التي تكشف أنها مجلة مفترسة.",
  },
  {
    title: "أسس البحث واختيار الفجوة البحثية",
    what: "تمييز الفجوة البحثية الحقيقية من الادّعاء، واستخراجها من الأدبيات المتاحة.",
    example: "راجِع مقترح فجوة صاغه باحث مبتدئ — أين ادّعى غياب الأبحاث دون مسح منهجي؟",
  },
  {
    title: "أنواع الأوراق البحثية",
    what: "مطابقة الهدف البحثي بنوع الورقة المناسب: تجريبية، مراجعة، دراسة حالة وغيرها.",
    example: "أمامك عدة مخطوطات — أيّها يمثّل بحثًا تجريبيًا فعلًا، وأيّها مراجعة سردية؟",
  },
  {
    title: "أجزاء الورقة البحثية",
    what: "تقييم العنوان والملخّص والكلمات المفتاحية، وتشريح بنية الورقة جزءًا جزءًا.",
    example: "افحص عنوانًا فيه حشو وكلمات مفتاحية فضفاضة — حدِّد ما يُفقدها قيمتها في الفهرسة.",
  },
  {
    title: "متطلبات النشر",
    what: "تضارب المصالح، إقرار مساهمات المؤلفين، خطاب التغطية، ومتطلبات المجلات الرصينة.",
    example: "إقرار مساهمات يُدرج ChatGPT ككاتب ثانٍ — حدِّد كل المخالفات وفق COPE/ICMJE.",
  },
  {
    title: "الإرسال والتتبع",
    what: "مسار المخطوطة من الفحص الفنّي والمراجعة الأولية حتى القرار والإنتاج ومنح الـDOI.",
    example: "رتّب مسار الورقة عبر نظام الإرسال من لحظة تقديمها حتى نشرها النهائي.",
  },
  {
    title: "الرحلة الكبرى",
    what: "محطة ختامية تجمع المحطات الستّ في مسار واحد متّصل.",
    example: "من الفجوة البحثية حتى الإرسال — رحلة كاملة في محطة واحدة.",
  },
];

const AR_DIGITS = ["١", "٢", "٣", "٤", "٥", "٦", "٧"];
const CHROME = [
  process.env.PUPPETEER_EXECUTABLE_PATH,
  "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium", "/usr/bin/chromium-browser",
].filter(Boolean).find((p) => existsSync(p));

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function stationSlides() {
  return STATIONS.map((s, i) => {
    const dots = STATIONS.map((_, j) => `<span class="dot${j === i ? " on" : ""}"></span>`).join("");
    return `
<section class="slide" data-shot="slide-${String(i + 2).padStart(2, "0")}-${i + 1}">
  <div class="pad grow"><div class="mid">
    <div class="eyebrow">المحطة ${AR_DIGITS[i]} من ٧</div>
    <div class="station-head">
      <span class="hex">${AR_DIGITS[i]}</span>
      <div class="station-title">${esc(s.title)}</div>
    </div>
    <div class="what">${esc(s.what)}</div>
    <div class="example">
      <span class="lbl">مثال على مهمّة حقيقية</span>
      <div class="txt">${esc(s.example)}</div>
    </div>
    </div>
    <div class="dots">${dots}</div>
  </div>
  <div class="foot"><span class="brand">رحلة الباحث</span><span class="mono">t.me/src_quize_bot</span></div>
</section>`;
  }).join("\n");
}

function posterRows() {
  return STATIONS.map((s, i) => `
    <div class="row${i === STATIONS.length - 1 ? " final" : ""}">
      <span class="n">${AR_DIGITS[i]}</span>
      <div class="txt"><div class="t">${esc(s.title)}</div><div class="d">${esc(s.what)}</div></div>
    </div>`).join("");
}

function fontUri(name) {
  const f = join(FONTS, `${name}.woff2`);
  if (!existsSync(f)) throw new Error(`missing font: ${f}`);
  return `data:font/woff2;base64,${readFileSync(f).toString("base64")}`;
}

function buildHtml() {
  let html = readFileSync(SRC, "utf8");
  html = html.replace("<!-- STATION_SLIDES -->", stationSlides());
  html = html.replace("<!-- POSTER_ROWS -->", posterRows());
  for (const n of [...new Set([...html.matchAll(/\{\{FONT:([A-Za-z0-9-]+)\}\}/g)].map((m) => m[1]))]) {
    html = html.replaceAll(`{{FONT:${n}}}`, fontUri(n));
  }
  const left = html.match(/\{\{[A-Z]+:[^}]+\}\}/g);
  if (left) throw new Error(`unresolved placeholders: ${[...new Set(left)].join(", ")}`);
  writeFileSync(OUT_HTML, html, "utf8");
  console.log(`wrote docs/launch/posters/carousel.html  (${(html.length / 1024) | 0} KB)`);
  return html;
}

async function renderPngs() {
  if (!CHROME) { console.log("no Chrome found — HTML written, PNGs skipped."); return; }
  const puppeteer = require("puppeteer-core");
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: "new",
    args: ["--no-sandbox", "--font-render-hinting=none", "--force-color-profile=srgb", "--hide-scrollbars"],
  });
  try {
    const page = await browser.newPage();
    // Slides are laid out at exact pixel sizes, so scale 1 gives exact output.
    await page.setViewport({ width: 1240, height: 1500, deviceScaleFactor: 1 });
    await page.goto(`file://${OUT_HTML}`, { waitUntil: "networkidle0" });
    await page.evaluate(() => document.fonts.ready);

    mkdirSync(OUT_PNG, { recursive: true });
    const targets = await page.$$("[data-shot]");
    const clipped = [];
    for (const el of targets) {
      const name = await el.evaluate((n) => n.dataset.shot);
      const box = await el.boundingBox();

      // Slides are a fixed size with overflow:hidden, so content that does not
      // fit is simply cut off and the render still looks plausible — a whole row
      // and the footer vanished this way once. Never ship a silent crop.
      const over = await el.evaluate((n) => {
        const worst = [...n.querySelectorAll("*")].reduce((m, c) => {
          const r = c.getBoundingClientRect(), p = n.getBoundingClientRect();
          return Math.max(m, r.bottom - p.bottom, p.top - r.top);
        }, 0);
        return Math.max(n.scrollHeight - n.clientHeight, Math.round(worst));
      });
      if (over > 1) clipped.push(`${name} (+${over}px)`);

      await el.screenshot({ path: join(OUT_PNG, `${name}.png`) });
      console.log(`  ${name}.png  ${Math.round(box.width)}x${Math.round(box.height)}${over > 1 ? `  ⚠ CLIPPED +${over}px` : ""}`);
    }
    if (clipped.length) {
      throw new Error(`content is cut off in: ${clipped.join(", ")} — tighten the layout`);
    }
  } finally {
    await browser.close();
  }
}

buildHtml();
if (!process.argv.includes("--html")) await renderPngs();
