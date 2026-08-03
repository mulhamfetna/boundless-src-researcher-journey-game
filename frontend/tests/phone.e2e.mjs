// Real-browser regression test for the phone play area (issue #15).
//
// The bug this locks in: `match`/`order` used to be taller than a phone screen,
// forcing a drag across a scrolling page. The first fix *looked* correct by
// measurement while silently CLIPPING text, because nested flex containers with
// `min-height:0` hide overflow instead of reporting it. Only a real browser at a
// real viewport catches that, so this test asserts three things at 360x640:
//
//   1. the page does not scroll,
//   2. nothing is clipped (every row is fully inside its scroll container),
//   3. the chip tray does not overlap the rows.
//
// Skips (exit 0) without Chrome. Run directly: `node frontend/tests/phone.e2e.mjs`.
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
    "/opt/google/chrome/chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean);
  return candidates.find((p) => existsSync(p));
}

const chrome = findChrome();
if (!chrome) {
  console.log("SKIP phone.e2e: no Chrome binary found (set PUPPETEER_EXECUTABLE_PATH to enable).");
  process.exit(0);
}

const puppeteer = (await import("puppeteer-core")).default;

// The longest real strings in the question bank — the worst case for fitting.
const MATCH_Q = {
  id: 1, type: "match", prompt_ar: "طابِق كل موقف بالإجراء الصحيح",
  left_ar: [
    "دراسة (أ) تقول إن غاز الشيمتك يُتلف الأنسجة بنسبة 80%، ودراسة (ب) في نفس الظروف تقول إنه آمن تمامًا.",
    "كل أبحاث الفلترة استخدمت مسحًا كيفيًا استطلاعيًا، ولا دراسة كمّية تقيس معدّل الترشيح بالدقيقة.",
    "«جُمعت عيّنات دم من 50 متطوّعًا وطُبّق المركّب الجديد مباشرة» دون ذكر موافقة لجنة الأخلاقيات.",
    "عشرات الدراسات تناولت أثر التلوّث على البالغين، ولا دراسة واحدة على الأطفال وكبار السن."],
  right_ar: ["تعارض نتائج", "فجوة منهجية", "خرق أخلاقي", "فجوة سكانية"],
  correct_pairs: [[0, 0], [1, 1], [2, 2], [3, 3]],
};
const ORDER_Q = {
  id: 2, type: "order", prompt_ar: "رتّب خطوات تقييم المجلة قبل الإرسال",
  items_ar: [
    "تحقّق من فهرسة المجلة في قواعد بيانات معتمدة مثل Scopus أو Web of Science",
    "افحص هيئة التحرير: أسماء حقيقية وانتماءات مؤسسية يمكن التحقق منها",
    "اقرأ سياسة رسوم النشر ومتى تُدفع، وتأكّد أنها ليست قبل المراجعة",
    "راجع متوسط زمن المراجعة المعلن وقارنه بالمعقول في تخصصك",
    "تأكّد من سياسة الأرشفة الرقمية وحقوق المؤلف قبل الإرسال"],
  correct_sequence: [0, 1, 2, 3, 4],
};

const html = readFileSync(join(FE, "index.html"), "utf8")
  .replace(/<script src="https:\/\/telegram[^"]*"><\/script>/, "");

let failures = 0;
const check = (ok, msg) => { console.log(`${ok ? "✓" : "✗"} ${msg}`); if (!ok) failures++; };

const browser = await puppeteer.launch({
  executablePath: chrome, headless: "new", args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

for (const [name, q] of [["match", MATCH_Q], ["order", ORDER_Q]]) {
  const page = await browser.newPage();
  await page.setViewport({ width: 360, height: 640, deviceScaleFactor: 2 });
  await page.setContent(html, { waitUntil: "load" });
  await page.addStyleTag({ path: join(FE, "styles.css") });
  for (const f of ["store.js", "game.js", "sprites.js", "ui.js", "card.js", "app.js"]) {
    await page.addScriptTag({ path: join(FE, f) });
  }
  await page.evaluate((q) => {
    state.questions = [q]; state.idx = 0;
    show("runner");
    document.getElementById("q-prompt").textContent = q.prompt_ar;
    if (q.type === "match") renderMatch(q); else renderOrder(q);
    fitPlayArea();
  }, q);
  await new Promise((r) => setTimeout(r, 300));

  const m = await page.evaluate(() => {
    const opts = document.getElementById("q-options");
    const rows = [...opts.querySelectorAll(".match-row, .order-row")];
    // A row is clipped if it falls outside ANY ancestor that hides overflow —
    // not just #q-options. The original bug clipped inside .match-list, so
    // checking only the outer box reported a false pass.
    const clippers = (el) => {
      const out = [];
      for (let p = el.parentElement; p; p = p.parentElement) {
        const ov = getComputedStyle(p).overflowY;
        if (ov === "hidden" || ov === "auto" || ov === "scroll") out.push(p);
        if (p === document.body) break;
      }
      return out;
    };
    const clipped = rows.filter((r) => {
      const b = r.getBoundingClientRect();
      return clippers(r).some((p) => {
        const pb = p.getBoundingClientRect();
        return b.top < pb.top - 1 || b.bottom > pb.bottom + 1;
      });
    }).length;
    // Does the tray sit on top of any row?
    const tray = opts.querySelector(".chip-tray");
    let overlapping = 0;
    if (tray) {
      const t = tray.getBoundingClientRect();
      overlapping = rows.filter((r) => {
        const b = r.getBoundingClientRect();
        return b.bottom > t.top + 1 && b.top < t.bottom - 1;
      }).length;
    }
    return {
      pageScrolls: document.documentElement.scrollHeight > window.innerHeight + 1,
      innerOverflow: opts.scrollHeight > opts.clientHeight + 1,
      rows: rows.length, clipped, overlapping,
      fontSize: getComputedStyle(opts).fontSize,
    };
  });

  console.log(`\n[${name}] rows=${m.rows} font=${m.fontSize}`);
  check(!m.pageScrolls, `${name}: the page does not scroll`);
  check(!m.innerOverflow, `${name}: the play area does not overflow`);
  check(m.clipped === 0, `${name}: no row is clipped (${m.clipped} clipped)`);
  check(m.overlapping === 0, `${name}: the chip tray overlaps nothing (${m.overlapping} overlapped)`);
  await page.close();
}

await browser.close();

if (failures) { console.error(`\nphone.e2e FAILED (${failures})`); process.exit(1); }
console.log("\nphone.e2e passed");
