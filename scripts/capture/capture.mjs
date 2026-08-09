/**
 * Drive the real Mini App in Chrome and capture screenshots / frame sequences.
 *
 * Everything the launch kit and the player handbook show must come from the
 * running product, not a mockup — a hand-drawn "screenshot" of a UI that no
 * longer exists is worse than none, and the handbook is meant to be reproducible
 * long after this session.
 *
 * How it authenticates: Telegram hands a Mini App its `initData` in the URL
 * fragment as `tgWebAppData`, and the backend verifies it with an HMAC keyed by
 * the bot token. So we sign a demo user with a throwaway token, hand it over the
 * real mechanism, and the real `telegram-web-app.js` parses it exactly as in
 * production. Nothing is stubbed: scoring, reports, badges and the leaderboard
 * are produced by the real server against a throwaway database.
 *
 * `tgWebAppVersion` is deliberately 6.0 — that is below the CloudStorage support
 * threshold, so the library's version guard throws synchronously and the app
 * falls back to localStorage. Declaring a supporting version would leave the app
 * waiting on a Telegram client that is not there (see issue #48).
 *
 * Usage (see run.sh, which starts the server for you):
 *   node scripts/capture/capture.mjs --probe            # dump DOM state, capture nothing
 *   node scripts/capture/capture.mjs --scene map
 *   node scripts/capture/capture.mjs --scene all
 */
import crypto from "node:crypto";
import { mkdirSync, existsSync, writeFileSync, rmSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
// puppeteer-core is a frontend dev dependency; resolve it from there.
const require = createRequire(join(REPO, "frontend", "package.json"));

const BASE = process.env.CAPTURE_BASE_URL || "http://localhost:8077";
const TOKEN = process.env.CAPTURE_BOT_TOKEN || "1234567:CAPTURE-DEV-TOKEN-NOT-REAL";
const OUT = process.env.CAPTURE_OUT || join(REPO, "docs", "launch", "assets");

// A phone that is neither the smallest nor the largest common size. deviceScaleFactor
// 2 gives retina-sharp PNGs that survive being placed in a PDF.
const VIEWPORT = { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true };

const DEMO_USER = { id: 777001, first_name: "باحثة", username: "demo_researcher", language_code: "ar" };
const DEMO_NAME = "سارة";

/**
 * In-world vocabulary. The game is themed, and much of the question text is
 * written in that world — but the public launch material is aimed at
 * researchers who have never heard of any of it, and a clip that opens with an
 * unexplained proper noun spends the viewer's attention on the wrong thing.
 * Recorded beats therefore prefer questions carrying none of these; the theme
 * stays where it belongs, inside the game.
 */
const LORE_TERMS = ["زاون", "بيلتوفر", "هكستيك", "الشيمر", "شيمر", "Zaun", "Piltover", "Hextech"];

function findChrome() {
  return [
    process.env.PUPPETEER_EXECUTABLE_PATH,
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean).find((p) => existsSync(p));
}

/** Sign initData exactly as Telegram does, so backend/app/auth.py accepts it. */
function signInitData(user, token) {
  const pairs = { auth_date: "1770000000", query_id: "AAEcapture", user: JSON.stringify(user) };
  const dcs = Object.keys(pairs).sort().map((k) => `${k}=${pairs[k]}`).join("\n");
  const secret = crypto.createHmac("sha256", "WebAppData").update(token).digest();
  const hash = crypto.createHmac("sha256", secret).update(dcs).digest("hex");
  return new URLSearchParams({ ...pairs, hash }).toString();
}

function appUrl() {
  const params = new URLSearchParams({
    tgWebAppData: signInitData(DEMO_USER, TOKEN),
    tgWebAppVersion: "6.0",
    tgWebAppPlatform: "android",
    tgWebAppThemeParams: JSON.stringify({ bg_color: "#0e1b33" }),
  });
  return `${BASE}/app/#${params.toString()}`;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Tap an element the way a phone does.
 *
 * Not a stylistic choice: chips and order rows call preventDefault() on
 * pointerdown for `pointerType === "mouse"` so a mouse can drag them, and a
 * cancelled pointerdown suppresses the compatibility click event — so a
 * synthetic mouse click silently does nothing. Touch skips the drag path
 * entirely (a finger cannot own both a drag and a scroll), which is the path
 * real players are on anyway.
 */
async function tap(page, selector) {
  await page.waitForSelector(selector, { visible: true, timeout: 8000 });
  await tapHandle(page, await page.$(selector), selector);
}

async function tapHandle(page, handle, label = "element") {
  // touchscreen.tap takes raw viewport coordinates and, unlike page.click(),
  // will NOT scroll the target into view first. A control below the fold — the
  // «تحقّق» button under six spot chips, say — then gets tapped at coordinates
  // that are off-screen or belong to something else, and the tap silently does
  // nothing at all. Scroll first, settle, then read the box.
  await handle.evaluate((el) => el.scrollIntoView({ block: "center", inline: "center" }));
  await sleep(120);
  const box = await handle.boundingBox();
  if (!box) throw new Error(`not tappable: ${label}`);
  await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
}

/** Wait for a screen to become the active one. */
async function waitScreen(page, name, timeout = 8000) {
  await page.waitForFunction(
    (n) => document.body.dataset.screen === n,
    { timeout, polling: 100 }, name,
  );
}

async function shot(page, name) {
  mkdirSync(OUT, { recursive: true });
  const path = join(OUT, `${name}.png`);
  await page.screenshot({ path });
  console.log(`  captured ${name}.png`);
  return path;
}

/** Complete onboarding so we land on the map as a named player. */
async function onboard(page) {
  await waitScreen(page, "onboarding");
  await page.type("#ob-name", DEMO_NAME, { delay: 60 });
  const avatar = await page.$("#ob-avatars button, #ob-avatars .ob-avatar");
  if (avatar) await tapHandle(page, avatar);
  await sleep(250);
  await tap(page, "#ob-start");
  await waitScreen(page, "home");
  await sleep(900); // let the map nodes and embers settle
}

/**
 * The mentor speaks before a station opens (ui.js mentorSay) and again at
 * several points during play. Nothing advances until it is dismissed.
 * Returns true if an overlay was actually present.
 */
async function dismissMentor(page, { pause = 0 } = {}) {
  // Two different overlays gate progress and both swallow taps aimed at what is
  // underneath: the mentor before/after a station, and the level-up card that
  // appears once the score lands. Missing the second one made every later tap
  // land on the overlay instead of the button, which looks exactly like a
  // button that does not work.
  const SELECTORS = [".mentor-overlay .mentor-next", ".levelup-overlay .levelup-next"];
  let dismissed = false;
  for (const sel of SELECTORS) {
    const btn = await page.$(sel);
    if (!btn) continue;
    if (pause) await sleep(pause);
    await tapHandle(page, btn, sel);
    await sleep(400);
    dismissed = true;
  }
  return dismissed;
}

/**
 * Enter a station by its visible title.
 *
 * The mentor overlay is inserted asynchronously, so waiting a fixed moment and
 * dismissing once is a race: miss it and we then wait forever for a runner that
 * the overlay is still covering. Poll for either outcome instead.
 */
async function enterStation(page, title) {
  const nodes = await page.$$(".map-node");
  let entered = false;
  for (const n of nodes) {
    const t = await n.evaluate((el) => el.querySelector(".node-title")?.textContent.trim());
    if (t === title) { await tapHandle(page, n, title); entered = true; break; }
  }
  if (!entered) throw new Error(`no station on the map titled: ${title}`);

  for (let i = 0; i < 40; i++) {           // ~10s
    if (await page.evaluate(() => document.body.dataset.screen) === "runner"
        && !await page.$(".mentor-overlay")) { await sleep(600); return; }
    await dismissMentor(page);
    await sleep(250);
  }
  throw new Error(`station did not open: ${title}`);
}

/**
 * Walk back to the map using the screens' own back buttons.
 *
 * Re-navigating to appUrl() looks equivalent but is not: the URL differs only
 * in its fragment, so Chrome performs a same-document navigation, the app never
 * re-boots, and the screen never changes.
 */
async function goHome(page) {
  const BACK = {
    report: "#btn-board",            // report has no direct home button
    board: "#btn-home",
    badges: "#btn-badges-home",
    progress: "#btn-progress-home",
    about: "#about-back",
    "report-issue": "#report-back",
    duel: "#duel-home",
  };
  const trail = [];
  for (let i = 0; i < 8; i++) {
    await dismissMentor(page);
    const screen = await page.evaluate(() => document.body.dataset.screen);
    trail.push(screen);
    if (screen === "home") { await sleep(500); return; }
    const sel = BACK[screen];
    if (!sel || !await page.$(sel)) throw new Error(`no way back from screen: ${screen}`);
    await tap(page, sel);
    await sleep(600);
  }
  throw new Error(`could not get back to the map (screens seen: ${trail.join(" → ")})`);
}

/** Leave a station without finishing it (the runner's ✕), landing on the map. */
async function exitToMap(page) {
  if (await page.evaluate(() => document.body.dataset.screen) === "runner") {
    await tap(page, "#q-exit-btn");
    await sleep(600);
    for (let i = 0; i < 3; i++) { if (!await dismissMentor(page)) break; }
  }
  await goHome(page);
}

async function openBrowser() {
  const chrome = findChrome();
  if (!chrome) {
    console.log("SKIP capture: no Chrome binary (set PUPPETEER_EXECUTABLE_PATH).");
    process.exit(0);
  }
  const puppeteer = require("puppeteer-core");
  const browser = await puppeteer.launch({
    executablePath: chrome,
    headless: "new",
    args: ["--no-sandbox", "--font-render-hinting=none", "--force-color-profile=srgb",
           "--hide-scrollbars", "--disable-lcd-text"],
  });
  const page = await browser.newPage();
  await page.setViewport(VIEWPORT);
  page.on("pageerror", (e) => console.log("  [pageerror]", e.message));
  page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("favicon.ico")) console.log(`  [HTTP ${r.status()}]`, r.url()); });
  await page.goto(appUrl(), { waitUntil: "networkidle0" });
  return { browser, page };
}

// ---------------------------------------------------------------------------
// Playing the game
//
// The answer key is already on the client — GET /questions ships it, by design
// (Khan-style checking; scoring is recomputed server-side anyway). So instead of
// hard-coding answers that would rot the moment content changes, each scene asks
// the running app what the correct answer is and performs the real interaction.
// ---------------------------------------------------------------------------

/** What the runner is showing right now, read from the app's own state. */
async function currentQuestion(page) {
  return page.evaluate(() => {
    const q = state.questions[state.idx];
    if (!q) return null;
    return { id: q.id, type: q.type, idx: state.idx, total: state.questions.length,
             prompt: (q.prompt_ar || "").slice(0, 70) };
  });
}

/** Answer the current question correctly, the way a player would. */
async function answerCorrectly(page, { pace = 450 } = {}) {
  const q = await currentQuestion(page);
  if (!q) return null;

  if (q.type === "mcq" || q.type === "tf" || q.type === "image") {
    const i = await page.evaluate(() => state.questions[state.idx].correct_index);
    const opts = await page.$$("#q-options .opt");
    await sleep(pace);
    await tapHandle(page, opts[i]);
    await sleep(1100);            // feedback shows, then recordAndAdvance fires at 700ms
  } else if (q.type === "spot") {
    const idxs = await page.evaluate(() => state.questions[state.idx].correct_indices);
    for (const i of idxs) {
      await sleep(pace);
      await tap(page, `.spot-chip[data-idx="${i}"]`);
    }
    await sleep(pace);
    await tap(page, ".runner-submit");   // «تحقّق»
    await sleep(900);
    await tap(page, ".runner-submit");   // becomes «التالي ➜»
    await sleep(500);
  } else if (q.type === "match") {
    const pairs = await page.evaluate(() => state.questions[state.idx].correct_pairs);
    for (const [left, right] of pairs) {
      await sleep(pace);
      await tap(page, `.chip[data-right="${right}"]`);
      await sleep(220);
      await tap(page, `.slot[data-left="${left}"]`);
    }
    await sleep(pace);
    await tap(page, ".runner-submit");
    await sleep(1100);
  } else if (q.type === "order") {
    const seq = await page.evaluate(() => state.questions[state.idx].correct_sequence);
    for (const orig of seq) {
      await sleep(pace);
      await tap(page, `.order-row[data-orig="${orig}"]`);
    }
    await sleep(pace);
    await tap(page, ".runner-submit");
    await sleep(1100);
  } else {
    throw new Error(`no driver for question type: ${q.type}`);
  }

  // A fun fact interrupts every fifth question.
  if (await page.$("#screen-funfact:not(.hidden)")) {
    await sleep(600);
    await tap(page, "#funfact-continue");
    await sleep(500);
  }
  await dismissMentor(page);
  return q;
}

/**
 * Play forward until a question of `type` is on screen, without answering it.
 * The question sample is random and concept-balanced, so a station does not
 * always contain a given type — returns false rather than looping forever.
 */
async function advanceUntilType(page, type, { pace = 120, avoidBoss = false, avoidLore = false } = {}) {
  for (let guard = 0; guard < 25; guard++) {
    const q = await currentQuestion(page);
    if (!q) return false;
    // The boss question wears a banner naming an in-world event, and much of the
    // question text is written in the game's world. Both belong inside the game,
    // not in a clip aimed at people who have never heard of any of it.
    const isBoss = await page.evaluate(() => state.bossId != null
      && state.questions[state.idx] && state.questions[state.idx].id === state.bossId);
    const hasLore = await page.evaluate((terms) => {
      const cur = state.questions[state.idx];
      const text = [cur.prompt_ar, ...(cur.options_ar || []), ...(cur.items_ar || [])].join(" ");
      return terms.some((t) => text.includes(t));
    }, LORE_TERMS);
    if (q.type === type && !(avoidBoss && isBoss) && !(avoidLore && hasLore)) return true;
    await answerCorrectly(page, { pace });
    if (await page.evaluate(() => document.body.dataset.screen) !== "runner") return false;
  }
  return false;
}

/** Dump enough DOM to write a new scene against, without capturing anything. */
async function probe(page) {
  await onboard(page);
  const map = await page.evaluate(() => ({
    screen: document.body.dataset.screen,
    hud: document.getElementById("map-hud")?.textContent.trim().slice(0, 80),
    nodes: [...document.querySelectorAll(".map-node")].map((n) => ({
      cls: n.className, title: n.querySelector(".node-title")?.textContent,
    })),
  }));
  console.log("MAP", JSON.stringify(map, null, 2));

  if (map.nodes.length) {
    await enterStation(page, map.nodes[0].title);
    const runner = await page.evaluate(() => ({
      screen: document.body.dataset.screen,
      prompt: document.getElementById("q-prompt")?.textContent.trim().slice(0, 90),
      progress: document.getElementById("progress")?.textContent.trim(),
      passageVisible: !document.getElementById("q-passage")?.classList.contains("hidden"),
      imageVisible: !document.getElementById("q-image")?.classList.contains("hidden"),
      optionsHTML: document.getElementById("q-options")?.innerHTML.slice(0, 600),
      optionClasses: [...document.querySelectorAll("#q-options *")].slice(0, 10).map((e) => e.className),
    }));
    console.log("RUNNER", JSON.stringify(runner, null, 2));
  }
}

const SCENES = {
  async map(page) { await onboard(page); await shot(page, "screen-map"); },

  /**
   * The launch clip.
   *
   * Shows the two interactions that actually distinguish the product — spotting
   * predatory-journal red flags, and ordering the real submission pipeline —
   * bracketed by the map and the score. Both are things a researcher *does*,
   * which is the whole pitch; a clip of someone picking a definition off a list
   * would sell the opposite of what this is.
   *
   * Recorded as separate takes and concatenated, so each beat is paced for a
   * viewer rather than at whatever speed the driver happens to run.
   */
  async clip(page) {
    const work = mkdtempSync(join(tmpdir(), "rj-clip-"));
    const takes = {};
    const take = async (name, fn) => {
      const path = join(work, `${name}.webm`);
      const rec = await page.screencast({ path });
      try { await fn(); } finally { await rec.stop(); }
      takes[name] = path;
      console.log(`  take ${name}`);
    };

    await onboard(page);
    await take("map", () => sleep(1900));

    // Beat 1 — spotting what is wrong with a real submission. Several stations
    // carry a `spot` question; take the first that is neither the boss nor
    // written in the game's world.
    let spotFound = false;
    for (const station of ["متطلبات النشر", "الإرسال والتتبع", "تصنيف المجلات العلمية"]) {
      await enterStation(page, station);
      if (await advanceUntilType(page, "spot", { pace: 60, avoidBoss: true, avoidLore: true })) {
        spotFound = true; break;
      }
      await exitToMap(page);
    }
    if (spotFound) {
      const idxs = await page.evaluate(() => state.questions[state.idx].correct_indices);
      await take("spot", async () => {
        await sleep(800);
        for (const i of idxs) { await tap(page, `.spot-chip[data-idx="${i}"]`); await sleep(470); }
        await sleep(250);
        await tap(page, ".runner-submit");        // «تحقّق»
        await sleep(1400);                        // hold on the green verdict
      });
      await tap(page, ".runner-submit");          // «التالي ➜», off camera
      await sleep(500);
    } else {
      console.log("  ! no lore-free spot question found — beat skipped");
    }

    // Finish the station off camera, so the score on screen is genuinely earned.
    for (let i = 0; i < 25; i++) {
      if (await page.evaluate(() => document.body.dataset.screen) !== "runner") break;
      if (!await answerCorrectly(page, { pace: 60 })) break;
    }
    await sleep(1400);
    for (let i = 0; i < 4; i++) { if (!await dismissMentor(page)) break; }
    if (await page.evaluate(() => document.body.dataset.screen) === "report") {
      // Hold on the headline. The per-question review below it quotes the
      // question text, which is written in the game's world — unreadable at clip
      // speed, but there is no reason to put it on screen.
      await page.evaluate(() => document.getElementById("screen-report")?.scrollTo(0, 0));
      await sleep(200);
      await take("report", () => sleep(2400));
    }

    // Beat 2 — ordering the real submission pipeline.
    await goHome(page);
    await enterStation(page, "الإرسال والتتبع");
    if (await advanceUntilType(page, "order", { pace: 60, avoidBoss: true, avoidLore: true })) {
      const seq = await page.evaluate(() => state.questions[state.idx].correct_sequence);
      await take("order", async () => {
        await sleep(800);
        for (const orig of seq) { await tap(page, `.order-row[data-orig="${orig}"]`); await sleep(450); }
        await sleep(1200);   // hold on the completed sequence
      });
      // Submitting is deliberately off camera: a correct match/order calls
      // nextStep() immediately, with no pause on the verdict, so keeping the
      // camera rolling would cut straight into an unrelated question.
      await tap(page, ".runner-submit");
    } else {
      console.log("  ! no lore-free order question in this sample — beat skipped");
    }

    // Narrative order, not recording order.
    const sequence = ["map", "spot", "order", "report"].filter((n) => takes[n]);
    if (!sequence.length) throw new Error("no takes recorded");
    mkdirSync(OUT, { recursive: true });
    const list = join(work, "list.txt");
    writeFileSync(list, sequence.map((n) => `file '${takes[n]}'`).join("\n"));

    const mp4 = join(OUT, "gameplay.mp4");
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list,
      "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
      "-vf", "scale=540:-2", "-movflags", "+faststart", mp4]);

    // A GIF for places that will not autoplay video. Palette-generated, or the
    // dark navy gradient bands badly.
    const pal = join(work, "pal.png");
    const gif = join(OUT, "gameplay.gif");
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", mp4,
      "-vf", "fps=12,scale=320:-2:flags=lanczos,palettegen=stats_mode=diff", pal]);
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", mp4, "-i", pal,
      "-lavfi", "fps=12,scale=320:-2:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3", gif]);

    rmSync(work, { recursive: true, force: true });
    console.log(`  beats: ${sequence.join(" → ")}`);
    console.log("  wrote gameplay.mp4 + gameplay.gif");
  },

  /** Every screen the handbook documents, captured from the running app. */
  async screens(page) {
    await shot(page, "screen-onboarding");          // we are on it before onboarding
    await onboard(page);
    await shot(page, "screen-map");

    // Each task type, on a lore-free question wherever the sample offers one.
    const TYPES = ["mcq", "tf", "image", "match", "order", "spot"];
    const captured = new Set();
    for (const station of ["متطلبات النشر", "الإرسال والتتبع", "تصنيف المجلات العلمية",
                           "أجزاء الورقة البحثية", "أنواع الأوراق البحثية العلمية"]) {
      if (TYPES.every((t) => captured.has(t))) break;
      await enterStation(page, station);
      for (let guard = 0; guard < 20; guard++) {
        if (await page.evaluate(() => document.body.dataset.screen) !== "runner") break;
        const q = await currentQuestion(page);
        if (!q) break;
        if (TYPES.includes(q.type) && !captured.has(q.type)) {
          await sleep(400);
          await shot(page, `task-${q.type}`);
          captured.add(q.type);
        }
        if (!await answerCorrectly(page, { pace: 60 })) break;
      }
      if (await page.evaluate(() => document.body.dataset.screen) === "runner") await exitToMap(page);
      else {
        for (let i = 0; i < 4; i++) { if (!await dismissMentor(page)) break; }
        if (await page.evaluate(() => document.body.dataset.screen) === "report") {
          await page.evaluate(() => document.getElementById("screen-report")?.scrollTo(0, 0));
          await sleep(200);
          await shot(page, "screen-report");
          await tap(page, "#btn-board");
          await sleep(1000);
          await shot(page, "screen-board");
        }
        await goHome(page);
      }
    }
    const missing = TYPES.filter((t) => !captured.has(t));
    if (missing.length) console.log(`  ! task types not drawn in these samples: ${missing.join(", ")}`);

    for (const [btn, screen, name] of [
      ["#btn-my-badges", "badges", "screen-badges"],
      ["#btn-my-progress", "progress", "screen-progress"],
      ["#btn-about", "about", "screen-about"],
      ["#btn-report", "report-issue", "screen-report-issue"],
    ]) {
      await tap(page, btn);
      await sleep(1200);
      if (await page.evaluate(() => document.body.dataset.screen) === screen) await shot(page, name);
      await goHome(page);
    }
  },

  /** Play one station end to end — proves the driver handles every task type. */
  async smoke(page) {
    await onboard(page);
    await enterStation(page, "تصنيف المجلات العلمية");
    const seen = [];
    for (let i = 0; i < 25; i++) {
      if (await page.evaluate(() => document.body.dataset.screen) !== "runner") break;
      const q = await answerCorrectly(page, { pace: 80 });
      if (!q) break;
      seen.push(`${q.idx + 1}/${q.total} ${q.type}`);
    }
    await sleep(1500);
    const end = await page.evaluate(() => ({
      screen: document.body.dataset.screen,
      summary: document.getElementById("report-summary")?.textContent.trim().slice(0, 120),
    }));
    console.log("  answered:", seen.join(" · "));
    console.log("  ended on:", JSON.stringify(end));
  },
};

async function main() {
  const args = process.argv.slice(2);
  const sceneArg = args.includes("--scene") ? args[args.indexOf("--scene") + 1] : null;
  const { browser, page } = await openBrowser();
  try {
    if (args.includes("--probe") || !sceneArg) { await probe(page); return; }
    const names = sceneArg === "all" ? Object.keys(SCENES) : [sceneArg];
    for (const n of names) {
      if (!SCENES[n]) throw new Error(`unknown scene: ${n}`);
      console.log(`scene: ${n}`);
      await SCENES[n](page);
    }
  } finally {
    await browser.close();
  }
}

main().catch((e) => { console.error("capture failed:", e.message); process.exit(1); });
