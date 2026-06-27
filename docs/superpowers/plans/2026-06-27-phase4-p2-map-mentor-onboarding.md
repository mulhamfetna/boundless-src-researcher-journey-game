# Phase 4 · P2 — Journey Map + Mentor + Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain quiz list with a mentor-guided journey: a first-run onboarding (name + avatar), a map of the 4 stages with done/next/open states, and a mentor bubble before each stage.

**Architecture:** Still frontend-only. New `store.js` persists the profile via Telegram CloudStorage (localStorage fallback); new `game.js` holds pure `mapState`/mentor copy; `ui.js` gains a `mentorSay` overlay. `app.js`'s `loadHome` becomes a router (onboarding vs. map) and renders the map from `/api/quizzes` + `/me/dashboard`. Existing runner/report/board/badges/progress flow is unchanged; all existing element IDs used by tests are preserved.

**Tech Stack:** Dependency-free HTML/CSS/JS; Vitest + jsdom; the existing `drag.e2e.mjs` browser test.

## Global Constraints

- **Frontend-only.** No backend/API/DB/content change **except** extending `main.py`'s cache-busting list to the new JS files (Task 5).
- **Reuse existing endpoints only:** `GET /api/quizzes`, `GET /api/me/dashboard` (for `stats.best_by_quiz`), `GET /api/quizzes/{slug}/questions`, `POST .../submit`.
- **Persistence** via `Telegram.WebApp.CloudStorage` with **localStorage fallback**; keys `rq_name`, `rq_avatar`, `rq_onboarded`.
- **Soft path:** every stage node is tappable; status (`done`/`next`/`open`) is visual only. `done` = quiz appears in `best_by_quiz`; the first non-done stage in order is `next`; the rest `open`.
- **Arabic, RTL**; **CSS/SVG/emoji only**.
- **Preserve element IDs used by tests/flow:** `#screen-runner`, `#screen-funfact`, `#q-options`, `.order-row`, `.chip`, `.slot`, `.opt`, `#btn-my-badges`, `#btn-my-progress`, and the `screen-*` set. New screen ids: `screen-onboarding` (added); `screen-home` is repurposed as the map.
- **The boot call must stay `loadHome().catch(<single line>)`** so `runner.test.js`/`drag.e2e.mjs` (which strip it via `/loadHome\(\)\.catch[^\n]*\n?/`) keep working. New module globals (`loadProfile`, `saveProfile`, `mapState`, `mentorLineFor`, `mentorSay`) must only be referenced inside map/onboarding functions (never at top level or inside `startQuiz`/`nextStep`/`renderQuestion`/`renderReport`), so `app.js` still evaluates standalone in tests.
- **Script load order in `index.html`:** `store.js`, `game.js`, `ui.js`, then `app.js`.
- **All existing tests stay green:** `./scripts/test.sh` (pytest 106 + vitest 7 + drag e2e).
- Tests run from `frontend/` (`npm test`).

---

## File Structure

```
frontend/
  store.js                  # CREATE: loadProfile/saveProfile (CloudStorage + localStorage)
  game.js                   # CREATE: mapState, MENTOR, mentorLineFor (pure)
  ui.js                     # MODIFY: add mentorSay(text, {onDone}) overlay
  index.html                # MODIFY: screen-onboarding + map markup; script includes
  app.js                    # MODIFY: loadHome router, renderMap, enterStage, showOnboarding, boot catch, screens[]
  styles.css                # MODIFY: mentor/map/onboarding styles
  tests/store.test.js       # CREATE
  tests/game.test.js        # CREATE
  tests/ui.test.js          # MODIFY: add mentorSay tests
backend/app/main.py         # MODIFY: cache-busting hash+regex include store.js, game.js
```

---

### Task 1: `store.js` — profile persistence (TDD)

**Files:**
- Create: `frontend/store.js`, `frontend/tests/store.test.js`

**Interfaces:**
- Produces (on `window`):
  - `loadProfile() -> Promise<{name:string, avatar:string, onboarded:boolean}>` — reads Telegram
    CloudStorage if present, else localStorage; defaults `avatar:"🧑‍🎓"`, `onboarded:false`.
  - `saveProfile(partial) -> Promise<true>` — writes any of `{name, avatar, onboarded}` to
    localStorage and (if present) CloudStorage. Keys: `rq_name`, `rq_avatar`, `rq_onboarded`
    (`onboarded` stored as `"1"`/`"0"`).

- [ ] **Step 1: Write the failing tests** in `frontend/tests/store.test.js`

```javascript
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "store.js"), "utf8");

function load() {
  delete window.Telegram; // force localStorage fallback
  new Function("window", "document", "localStorage", src)(window, document, window.localStorage);
}

describe("store (profile persistence)", () => {
  beforeEach(() => { window.localStorage.clear(); load(); });

  it("defaults when nothing stored", async () => {
    const p = await window.loadProfile();
    expect(p).toEqual({ name: "", avatar: "🧑‍🎓", onboarded: false });
  });

  it("round-trips via localStorage fallback", async () => {
    await window.saveProfile({ name: "لينا", avatar: "🦊", onboarded: true });
    const p = await window.loadProfile();
    expect(p.name).toBe("لينا");
    expect(p.avatar).toBe("🦊");
    expect(p.onboarded).toBe(true);
  });

  it("partial save leaves other fields at defaults", async () => {
    await window.saveProfile({ name: "سامي" });
    const p = await window.loadProfile();
    expect(p.name).toBe("سامي");
    expect(p.avatar).toBe("🧑‍🎓");
    expect(p.onboarded).toBe(false);
  });

  it("prefers CloudStorage when available", async () => {
    const mem = { rq_name: "كلاود", rq_avatar: "🦉", rq_onboarded: "1" };
    window.Telegram = { WebApp: { CloudStorage: {
      getItems: (keys, cb) => cb(null, Object.fromEntries(keys.map(k => [k, mem[k] || ""]))),
      setItem: (k, v, cb) => { mem[k] = v; cb(null, true); },
    } } };
    new Function("window", "document", "localStorage", src)(window, document, window.localStorage);
    const p = await window.loadProfile();
    expect(p.name).toBe("كلاود");
    expect(p.avatar).toBe("🦉");
    expect(p.onboarded).toBe(true);
  });
});
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd frontend && npm test -- store`
Expected: FAIL — cannot read `../store.js`.

- [ ] **Step 3: Create `frontend/store.js`**

```javascript
(function () {
  const K = { name: "rq_name", avatar: "rq_avatar", onboarded: "rq_onboarded" };

  function cloud() {
    const tg = window.Telegram && window.Telegram.WebApp;
    return tg && tg.CloudStorage ? tg.CloudStorage : null;
  }
  function cloudGet(keys) {
    return new Promise((resolve) => {
      const cs = cloud();
      if (!cs) return resolve(null);
      try { cs.getItems(keys, (err, res) => resolve(err ? null : res)); }
      catch (_) { resolve(null); }
    });
  }
  function cloudSet(k, v) {
    return new Promise((resolve) => {
      const cs = cloud();
      if (!cs) return resolve(false);
      try { cs.setItem(k, v, () => resolve(true)); } catch (_) { resolve(false); }
    });
  }
  function ls() { return typeof localStorage !== "undefined" ? localStorage : null; }

  async function loadProfile() {
    const res = await cloudGet([K.name, K.avatar, K.onboarded]);
    const get = (k) => {
      if (res && res[k] != null && res[k] !== "") return res[k];
      const s = ls();
      return s ? s.getItem(k) : null;
    };
    return {
      name: get(K.name) || "",
      avatar: get(K.avatar) || "🧑‍🎓",
      onboarded: (get(K.onboarded) || "") === "1",
    };
  }

  async function saveProfile(partial) {
    const pairs = [];
    if (partial.name != null) pairs.push([K.name, partial.name]);
    if (partial.avatar != null) pairs.push([K.avatar, partial.avatar]);
    if (partial.onboarded != null) pairs.push([K.onboarded, partial.onboarded ? "1" : "0"]);
    const s = ls();
    for (const [k, v] of pairs) {
      if (s) s.setItem(k, v);
      await cloudSet(k, v);
    }
    return true;
  }

  window.loadProfile = loadProfile;
  window.saveProfile = saveProfile;
})();
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd frontend && npm test -- store`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/store.js frontend/tests/store.test.js
git commit -m "feat(p2): profile persistence via CloudStorage + localStorage (store.js)"
```

---

### Task 2: `game.js` — map state + mentor copy (TDD)

**Files:**
- Create: `frontend/game.js`, `frontend/tests/game.test.js`

**Interfaces:**
- Produces (on `window`):
  - `mapState(quizzes, dashboard) -> [{slug, title_ar, index, status}]` — `status ∈ done|next|open`.
  - `MENTOR` — keyed Arabic copy incl. `welcome`, `welcome_anon`, `stage:{slug}`, `boss`, `levelUp`,
    `victory`, `encourage`.
  - `mentorLineFor(key, ctx) -> string` — supports `"stage:<slug>"` keys and `{name}` interpolation.

- [ ] **Step 1: Write the failing tests** in `frontend/tests/game.test.js`

```javascript
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "game.js"), "utf8");
beforeEach(() => { new Function("window", src)(window); });

const QUIZZES = [
  { slug: "foundations", title_ar: "الأسس" },
  { slug: "paper-parts", title_ar: "الأجزاء" },
  { slug: "journals", title_ar: "المجلات" },
];

describe("mapState", () => {
  it("marks done from best_by_quiz, first non-done as next, rest open", () => {
    const dash = { stats: { best_by_quiz: { foundations: 120 } } };
    const s = window.mapState(QUIZZES, dash);
    expect(s.map(x => x.status)).toEqual(["done", "next", "open"]);
    expect(s[0].index).toBe(0);
  });

  it("first stage is next when nothing done", () => {
    const s = window.mapState(QUIZZES, { stats: { best_by_quiz: {} } });
    expect(s.map(x => x.status)).toEqual(["next", "open", "open"]);
  });

  it("handles missing dashboard", () => {
    const s = window.mapState(QUIZZES, null);
    expect(s[0].status).toBe("next");
  });
});

describe("mentorLineFor", () => {
  it("interpolates {name}", () => {
    expect(window.mentorLineFor("welcome", { name: "لينا" })).toContain("لينا");
  });
  it("resolves stage keys", () => {
    expect(window.mentorLineFor("stage:journals", {})).toContain("🕵️");
  });
  it("falls back for unknown keys", () => {
    expect(typeof window.mentorLineFor("nope", {})).toBe("string");
  });
});
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd frontend && npm test -- game`
Expected: FAIL — cannot read `../game.js`.

- [ ] **Step 3: Create `frontend/game.js`**

```javascript
(function () {
  function mapState(quizzes, dashboard) {
    const best = (dashboard && dashboard.stats && dashboard.stats.best_by_quiz) || {};
    let nextAssigned = false;
    return (quizzes || []).map((q, i) => {
      const done = best[q.slug] != null;
      let status;
      if (done) status = "done";
      else if (!nextAssigned) { status = "next"; nextAssigned = true; }
      else status = "open";
      return { slug: q.slug, title_ar: q.title_ar, index: i, status };
    });
  }

  const MENTOR = {
    welcome_anon: "أهلاً! أنا البروفيسور 🦉. أخبِرني باسمك واختَر رمزك، ولنبدأ رحلة الباحث!",
    welcome: "أهلاً بك يا {name}! أنا البروفيسور 🦉، وسأرافقك لتصبح باحثاً ناشراً.",
    stage: {
      foundations: "📚 أوّل محطّاتنا: أسس البحث — من هنا يبدأ كل باحث عظيم.",
      "paper-parts": "🧩 لنتعرّف على تشريح الورقة البحثية جزءاً جزءاً.",
      "paper-types": "📄 أنواع الأوراق كثيرة — لنتعلّم كيف نختار النوع الصحيح.",
      journals: "🕵️ مهمّة التحرّي: سنكشف المجلات المفترِسة ونختار المجلة المناسبة.",
    },
    boss: "👑 هذا تحدّي الزعيم! ركّز جيداً — إنه أصعب سؤال في المحطّة.",
    levelUp: "ارتقيتَ إلى مستوى جديد يا {name}! أنا فخور بك.",
    victory: "🎉 مبروك يا {name}! أكملتَ المحطّة كباحث حقيقي.",
    encourage: "لا بأس — الباحث الجيّد يتعلّم من المحاولة. واصِل!",
  };

  function mentorLineFor(key, ctx) {
    ctx = ctx || {};
    let raw;
    if (key.indexOf("stage:") === 0) raw = MENTOR.stage[key.slice(6)] || "هيا بنا!";
    else raw = MENTOR[key] || "هيا بنا!";
    return raw.replace(/\{name\}/g, ctx.name || "صديقي");
  }

  window.mapState = mapState;
  window.MENTOR = MENTOR;
  window.mentorLineFor = mentorLineFor;
})();
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd frontend && npm test -- game`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/game.js frontend/tests/game.test.js
git commit -m "feat(p2): map state + mentor copy (game.js)"
```

---

### Task 3: `ui.js` — `mentorSay` overlay (TDD) + styles

**Files:**
- Modify: `frontend/ui.js` (add `mentorSay`), `frontend/tests/ui.test.js` (add tests), `frontend/styles.css` (mentor overlay styles)

**Interfaces:**
- Consumes: nothing new. Produces: `window.mentorSay(text, opts={}) -> HTMLElement` — appends a
  full-screen `.mentor-overlay` (to `document.body`, NOT `#fx-layer`, which is pointer-events:none)
  containing a 🦉 card with `text` and a متابعة button; clicking the button or the backdrop removes
  the overlay and calls `opts.onDone` if a function.

- [ ] **Step 1: Add failing tests** to `frontend/tests/ui.test.js` (append a new describe block)

```javascript
describe("mentorSay", () => {
  beforeEach(() => { loadUi(); });

  it("renders an overlay with the given text", () => {
    window.mentorSay("مرحبا");
    const ov = document.querySelector(".mentor-overlay");
    expect(ov).not.toBeNull();
    expect(ov.querySelector(".mentor-text").textContent).toBe("مرحبا");
  });

  it("clicking متابعة removes the overlay and calls onDone", () => {
    let done = false;
    window.mentorSay("هيا", { onDone: () => { done = true; } });
    document.querySelector(".mentor-next").click();
    expect(document.querySelector(".mentor-overlay")).toBeNull();
    expect(done).toBe(true);
  });
});
```

(Note: `loadUi()` already exists at the top of `ui.test.js` from P1.)

- [ ] **Step 2: Run them, expect failure**

Run: `cd frontend && npm test -- ui`
Expected: FAIL — `window.mentorSay is not a function`.

- [ ] **Step 3: Add `mentorSay` to `frontend/ui.js`** — inside the IIFE, before the `window.confetti = …` exports, add:

```javascript
  function mentorSay(text, opts = {}) {
    const overlay = document.createElement("div");
    overlay.className = "mentor-overlay";
    overlay.innerHTML =
      '<div class="mentor-card"><div class="mentor-avatar">🦉</div>' +
      '<div class="mentor-text"></div><button class="mentor-next">متابعة</button></div>';
    overlay.querySelector(".mentor-text").textContent = text;
    const close = () => {
      overlay.remove();
      if (typeof opts.onDone === "function") opts.onDone();
    };
    overlay.querySelector(".mentor-next").onclick = close;
    overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
    document.body.appendChild(overlay);
    return overlay;
  }
```

And add to the exports block: `window.mentorSay = mentorSay;`

- [ ] **Step 4: Append mentor styles to `frontend/styles.css`**

```css
/* ---- P2 mentor ---- */
.mentor-overlay { position:fixed; inset:0; z-index:10000; display:flex; align-items:flex-end;
  justify-content:center; background:#0009; padding:18px; }
.mentor-card { background:linear-gradient(180deg,var(--card2),var(--card)); border-radius:18px;
  padding:18px; max-width:520px; width:100%; box-shadow:0 12px 40px #000a; animation:screen-in .25s ease; }
.mentor-avatar { font-size:2.4rem; text-align:center; }
.mentor-text { margin:10px 0 14px; font-size:1.05rem; line-height:1.8; text-align:center; }
.mentor-next { background:linear-gradient(180deg,var(--accent2),var(--accent)); font-weight:700; }
```

- [ ] **Step 5: Run the ui tests, expect pass**

Run: `cd frontend && npm test -- ui`
Expected: PASS (6 passed: 4 P1 + 2 mentorSay).

- [ ] **Step 6: Commit**

```bash
git add frontend/ui.js frontend/tests/ui.test.js frontend/styles.css
git commit -m "feat(p2): mentorSay bubble overlay + styles"
```

---

### Task 4: Onboarding + map screens (markup, app.js wiring, styles)

**Files:**
- Modify: `frontend/index.html` (repurpose `screen-home` as the map; add `screen-onboarding`; script includes)
- Modify: `frontend/app.js` (`screens[]`, `loadHome` router, `renderMap`, `enterStage`, `showOnboarding`, boot catch)
- Modify: `frontend/styles.css` (map + onboarding styles)

**Interfaces:**
- Consumes: `loadProfile`/`saveProfile` (Task 1), `mapState`/`mentorLineFor` (Task 2), `mentorSay` (Task 3), existing `startQuiz`/`loadBadges`/`loadDashboard`/`show`/`api`.
- Produces: a first-run onboarding and a journey map as the home screen.

- [ ] **Step 1: Edit `frontend/index.html`** — replace the `screen-home` section's body and the script
includes.

Replace the entire existing `<section id="screen-home" …> … </section>` block with:

```html
    <section id="screen-onboarding" class="screen hidden">
      <h1>رحلة الباحث</h1>
      <div id="ob-mentor"></div>
      <input id="ob-name" class="ob-name" placeholder="اكتب اسمك" />
      <div id="ob-avatars" class="ob-avatars"></div>
      <button id="ob-start" class="quiz-card">ابدأ الرحلة 🚀</button>
    </section>

    <section id="screen-home" class="screen">
      <h1>رحلة الباحث</h1>
      <div id="map-hud" class="map-hud"></div>
      <div id="map-path" class="map-path"></div>
      <div class="map-actions">
        <button id="btn-my-badges" class="quiz-card">🏅 أوسمتي</button>
        <button id="btn-my-progress" class="quiz-card">📊 تقدّمي</button>
      </div>
    </section>
```

Replace the three script lines at the end of `<body>` with (adds store.js + game.js before ui.js):

```html
  <div id="fx-layer"></div>
  <script src="store.js?v=p2"></script>
  <script src="game.js?v=p2"></script>
  <script src="ui.js?v=p2"></script>
  <script src="app.js?v=3a1"></script>
```

- [ ] **Step 2: Edit `frontend/app.js`** — register the onboarding screen in `screens`:

```javascript
const screens = ["home", "runner", "report", "board", "badges", "funfact", "progress", "onboarding"];
```

- [ ] **Step 3: Replace `loadHome` in `frontend/app.js`** with the router + map + onboarding.

Replace the entire existing `async function loadHome() { … }` with:

```javascript
const STAGE_EMOJI = { foundations: "📚", "paper-parts": "🧩", "paper-types": "📄", journals: "🕵️" };
const AVATARS = ["🧑‍🎓", "👩‍🎓", "🧑‍🔬", "👩‍🔬", "🧑‍💻", "🦉", "🦊", "🐱"];

async function loadHome() {
  const profile = await loadProfile();
  if (!profile.onboarded) return showOnboarding();
  return renderMap(profile);
}

async function renderMap(profile) {
  let quizzes = [];
  let dashboard = null;
  try { quizzes = await api("/quizzes"); } catch (_) {}
  try { dashboard = await api("/me/dashboard", { headers: { "X-Init-Data": tg.initData } }); } catch (_) {}

  const hud = document.getElementById("map-hud");
  hud.innerHTML =
    `<span class="hud-avatar">${profile.avatar}</span>` +
    `<span class="hud-name">${profile.name || "باحث"}</span>`;

  const path = document.getElementById("map-path");
  path.innerHTML = "";
  mapState(quizzes, dashboard).forEach((s) => {
    const node = document.createElement("div");
    node.className = "map-node " + s.status;
    const mark = s.status === "done" ? "✓" : (s.status === "next" ? "✦" : "");
    node.innerHTML =
      `<span class="node-emoji">${STAGE_EMOJI[s.slug] || "⭐"}</span>` +
      `<span class="node-title">${s.title_ar}</span>` +
      `<span class="node-mark">${mark}</span>`;
    node.onclick = () => enterStage(s.slug, profile);
    path.appendChild(node);
  });

  document.getElementById("btn-my-badges").onclick = loadBadges;
  document.getElementById("btn-my-progress").onclick = loadDashboard;
  show("home");
}

function enterStage(slug, profile) {
  const line = mentorLineFor("stage:" + slug, { name: profile.name });
  if (typeof mentorSay === "function") mentorSay(line, { onDone: () => startQuiz(slug) });
  else startQuiz(slug);
}

function showOnboarding() {
  const mentor = document.getElementById("ob-mentor");
  mentor.innerHTML =
    `<div class="mentor-card"><div class="mentor-avatar">🦉</div>` +
    `<div class="mentor-text">${mentorLineFor("welcome_anon", {})}</div></div>`;

  let chosen = AVATARS[0];
  const grid = document.getElementById("ob-avatars");
  grid.innerHTML = "";
  AVATARS.forEach((a, i) => {
    const b = document.createElement("span");
    b.className = "ob-avatar" + (i === 0 ? " selected" : "");
    b.textContent = a;
    b.onclick = () => {
      chosen = a;
      grid.querySelectorAll(".ob-avatar").forEach((x) => x.classList.remove("selected"));
      b.classList.add("selected");
    };
    grid.appendChild(b);
  });

  document.getElementById("ob-start").onclick = async () => {
    const name = (document.getElementById("ob-name").value || "").trim() || "باحث";
    await saveProfile({ name, avatar: chosen, onboarded: true });
    loadHome();
  };
  show("onboarding");
}
```

- [ ] **Step 4: Update the boot line** at the very bottom of `frontend/app.js` — keep it
strippable (matches `/loadHome\(\)\.catch[^\n]*\n?/`) but point the fallback at `#map-path`:

```javascript
loadHome().catch(() => { const m = document.getElementById("map-path"); if (m) m.textContent = "تعذّر التحميل"; });
```

- [ ] **Step 5: Append map + onboarding styles to `frontend/styles.css`**

```css
/* ---- P2 map + onboarding ---- */
.map-hud { display:flex; align-items:center; gap:10px; padding:12px; border-radius:14px;
  background:linear-gradient(180deg,var(--card2),var(--card)); margin-bottom:10px; box-shadow:inset 0 1px 0 #ffffff10; }
.map-hud .hud-avatar { font-size:1.8rem; }
.map-hud .hud-name { font-weight:700; }
.map-path { display:flex; flex-direction:column; gap:14px; margin:14px 0; }
.map-node { display:flex; align-items:center; gap:12px; padding:16px; border-radius:16px; cursor:pointer;
  background:linear-gradient(180deg,var(--card2),var(--card)); box-shadow:inset 0 1px 0 #ffffff10; transition:transform .08s ease; }
.map-node:active { transform:scale(.99); }
.map-node .node-emoji { font-size:1.6rem; }
.map-node .node-title { font-weight:700; flex:1; }
.map-node .node-mark { font-size:1.2rem; color:var(--gold); }
.map-node.done { outline:2px solid var(--good); }
.map-node.done .node-mark { color:var(--good); }
.map-node.next { outline:2px solid var(--gold); animation:node-pulse 1.6s ease-in-out infinite; }
@keyframes node-pulse { 0%,100%{box-shadow:0 0 0 0 #ffd16655;} 50%{box-shadow:0 0 0 8px #ffd16600;} }
.map-actions { display:flex; gap:8px; }
.map-actions .quiz-card { flex:1; }
.ob-name { width:100%; padding:12px; border-radius:12px; border:none; background:var(--card); color:var(--fg); font-size:1rem; text-align:center; }
.ob-avatars { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin:12px 0; }
.ob-avatar { font-size:1.8rem; padding:8px 12px; border-radius:12px; background:var(--card); cursor:pointer; }
.ob-avatar.selected { outline:2px solid var(--gold); }
```

- [ ] **Step 6: Verify standalone JS + existing tests still pass**

Run:
```bash
cd frontend && node --check app.js && node --check store.js && node --check game.js && node --check ui.js && npm test && node tests/drag.e2e.mjs
```
Expected: syntax OK; vitest passes (runner.test.js still works — `loadHome`'s new body and the
module globals are only invoked via the stripped boot / map UI, never in the tested paths); drag
e2e passes.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat(p2): onboarding + journey map home with mentor stage intros"
```

---

### Task 5: Cache-busting for new assets + full-suite gate + deploy

**Files:**
- Modify: `backend/app/main.py` (include `store.js`, `game.js` in the bundle hash + restamp regex)

**Interfaces:**
- Produces: all five frontend assets (`app.js`, `ui.js`, `store.js`, `game.js`, `styles.css`)
  carry the same auto-busted `?v=<bundle-sha8>`.

- [ ] **Step 1: Edit `backend/app/main.py`** — extend the hash file list:

```python
    for fn in ("app.js", "ui.js", "store.js", "game.js", "styles.css"):
```

and the restamp regex in `_serve_index`:

```python
            r"(app\.js|ui\.js|store\.js|game\.js|styles\.css)\?v=[A-Za-z0-9_]+",
```

- [ ] **Step 2: Backend suite (main.py change) stays green**

Run: `cd backend && pytest -q`
Expected: 106 passed.

- [ ] **Step 3: Full combined suite**

Run: `./scripts/test.sh`
Expected: backend 106; frontend vitest (3 runner + 4 ui + 2 mentorSay + 4 store + 6 game = 19);
drag e2e passes.

- [ ] **Step 4: Deploy (frontend-only; no reseed/migrate)**

Run: `cd .. && docker compose up -d --build`
Verify: `curl -s localhost:8000/health` → ok; `curl -s localhost:8000/app/ | grep -oE '(store|game|ui|app)\.js\?v=[a-z0-9]+'` shows all four sharing one hash (no literal `p2`); the served
`game.js` contains `mapState`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "fix(p2): cache-bust store.js + game.js with the bundle hash"
```

---

## Self-Review (completed by plan author)

**Spec coverage (P2 slice of §8):** journey map home with done/next/open (§4.1 `mapState`,
§4.4 map) → Tasks 2, 4 ✓; mentor guide bubbles (§4.3) → Tasks 2 (`mentorLineFor`), 3 (`mentorSay`),
4 (stage intro) ✓; onboarding name+avatar (§4.4) → Task 4 ✓; CloudStorage persistence (§4.2
`store.js`) → Task 1 ✓; soft path (all nodes tappable, status visual) → Task 4 (`node.onclick`
always wired) ✓. RPG systems (HUD level/XP/rank, avatar travel, boss) are P3, out of this plan.

**Placeholder scan:** No "TBD/handle later" — every function, test, and CSS block is concrete.

**Type consistency:** `loadProfile()`→`{name,avatar,onboarded}` (Task 1) matches `renderMap`/
`showOnboarding` usage (Task 4). `mapState(quizzes, dashboard)` (Task 2) matches the call in
`renderMap` (Task 4) and the dashboard shape `stats.best_by_quiz` (confirmed in Phase 3C).
`mentorSay(text,{onDone})` (Task 3) matches `enterStage` (Task 4). `mentorLineFor("stage:"+slug)`
(Task 4) matches the `stage:` handling in Task 2. The boot line stays
`loadHome().catch(<one line>)` per the strip-regex constraint.

## Out of scope (P3)
- `game.js` `levelFromXp`/`RANKS`/`pickBoss`; HUD level bar/XP/rank; avatar customization beyond
  onboarding pick; boss-question reframing; level-up overlay.
