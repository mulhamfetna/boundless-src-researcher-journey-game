# Phase 4 · P1 — Game Theme & Juice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the existing Mini App a cohesive game look and motion (deep-indigo + gold theme, glows, animations, confetti) without changing any screen flow or markup IDs.

**Architecture:** Pure presentation layer. A new `frontend/ui.js` adds reusable juice (`confetti`, `burst`) loaded before `app.js`; `styles.css` gets a new palette + component restyle + keyframe animations; `app.js` gains two guarded one-line hooks to fire confetti on a correct answer and on the victory report. Every existing element ID and class name is preserved, so the runner/report/board/badges/progress logic and tests are untouched.

**Tech Stack:** Dependency-free HTML/CSS/JS; Vitest + jsdom for `ui.js`; the existing `drag.e2e.mjs` browser test.

## Global Constraints

- **Frontend-only.** No backend/API/DB/content change.
- **Preserve every existing element ID and class name** used by `app.js` (e.g. `.opt`, `.quiz-card`, `#q-options`, `.order-row`, `.chip`, `.slot`, `.badge`, `.dash-stats`, `#screen-*`). Restyle them; do not rename or remove them.
- **Arabic, RTL** for any visible copy. **CSS/SVG/emoji only** — no image assets.
- **No unguarded new globals in `app.js`.** Calls into `ui.js` must be `typeof`-guarded so `app.js` still evaluates standalone (the `runner.test.js` harness loads `app.js` without `ui.js`).
- **All existing tests must stay green:** `cd backend && pytest -q` (106), `cd frontend && npm test` (3), `node frontend/tests/drag.e2e.mjs`.
- Frontend asset version auto-busts (`main.py` stamps `?v=<bundle-sha8>`); no manual `?v=` edit.
- Tests run from `frontend/` (`npm test`).

---

## File Structure

```
frontend/
  ui.js                  # CREATE: confetti(), burst(el) — reusable juice
  styles.css             # MODIFY: palette, component restyle, keyframe animations
  index.html             # MODIFY: <script src="ui.js"> before app.js; <div id="fx-layer">
  app.js                 # MODIFY: 2 guarded confetti hooks (correct answer + victory)
  tests/ui.test.js       # CREATE: confetti/burst behavior (jsdom + fake timers)
```

---

### Task 1: `ui.js` — confetti & burst (TDD)

**Files:**
- Create: `frontend/ui.js`, `frontend/tests/ui.test.js`

**Interfaces:**
- Produces (attached to `window` so `app.js` can call them, and exported-by-presence):
  - `confetti(opts = {})` — appends `opts.count` (default 24) `.confetti-piece` spans to
    `#fx-layer` (or `document.body` if absent), each with randomized CSS custom props; removes
    them after `opts.life` ms (default 1200). Returns the count created.
  - `burst(el, opts = {})` — same idea anchored near `el`'s center (default count 12). No-op if
    `el` is null.
- Randomness uses `Math.random()`; tests assert counts/cleanup, not exact positions.

- [ ] **Step 1: Write the failing tests** in `frontend/tests/ui.test.js`

```javascript
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const uiSrc = readFileSync(join(dir, "..", "ui.js"), "utf8");

function loadUi() {
  document.body.innerHTML = '<div id="fx-layer"></div><button id="b">x</button>';
  new Function("window", "document", uiSrc)(window, document);
}

describe("ui juice", () => {
  beforeEach(() => { vi.useFakeTimers(); loadUi(); });

  it("confetti creates the requested number of pieces in the fx layer", () => {
    const n = window.confetti({ count: 10, life: 500 });
    expect(n).toBe(10);
    expect(document.querySelectorAll("#fx-layer .confetti-piece").length).toBe(10);
  });

  it("confetti cleans up its pieces after life ms", () => {
    window.confetti({ count: 6, life: 500 });
    vi.advanceTimersByTime(600);
    expect(document.querySelectorAll(".confetti-piece").length).toBe(0);
  });

  it("confetti defaults to 24 pieces", () => {
    expect(window.confetti()).toBe(24);
  });

  it("burst anchored on an element creates pieces and is a no-op on null", () => {
    expect(window.burst(null)).toBe(0);
    const made = window.burst(document.getElementById("b"), { count: 8 });
    expect(made).toBe(8);
  });
});
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd frontend && npm test -- ui`
Expected: FAIL — cannot read `../ui.js` (file missing).

- [ ] **Step 3: Create `frontend/ui.js`**

```javascript
// Reusable visual juice. No dependencies. Functions are attached to window so
// app.js can call them via a typeof guard.
(function () {
  function layer() {
    return document.getElementById("fx-layer") || document.body;
  }

  function piece(x, y) {
    const el = document.createElement("span");
    el.className = "confetti-piece";
    const hue = Math.floor(Math.random() * 360);
    el.style.setProperty("--x", (Math.random() * 2 - 1).toFixed(2));
    el.style.setProperty("--r", Math.floor(Math.random() * 360) + "deg");
    el.style.setProperty("--d", (0.7 + Math.random() * 0.8).toFixed(2) + "s");
    el.style.left = x + "px";
    el.style.top = y + "px";
    el.style.background = `hsl(${hue} 90% 60%)`;
    return el;
  }

  function spawn(count, life, x, y) {
    const host = layer();
    for (let i = 0; i < count; i++) host.appendChild(piece(x, y));
    setTimeout(() => {
      host.querySelectorAll(".confetti-piece").forEach((p) => p.remove());
    }, life);
    return count;
  }

  function confetti(opts = {}) {
    const count = opts.count == null ? 24 : opts.count;
    const life = opts.life == null ? 1200 : opts.life;
    const w = window.innerWidth || 360;
    return spawn(count, life, w / 2, 40);
  }

  function burst(el, opts = {}) {
    if (!el) return 0;
    const count = opts.count == null ? 12 : opts.count;
    const life = opts.life == null ? 900 : opts.life;
    const r = el.getBoundingClientRect ? el.getBoundingClientRect() : { left: 0, top: 0, width: 0, height: 0 };
    return spawn(count, life, r.left + r.width / 2, r.top + r.height / 2);
  }

  window.confetti = confetti;
  window.burst = burst;
})();
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd frontend && npm test -- ui`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/ui.js frontend/tests/ui.test.js
git commit -m "feat(p1): reusable confetti/burst juice (ui.js)"
```

---

### Task 2: Game theme palette + component restyle

**Files:**
- Modify: `frontend/styles.css` (replace the `:root` palette and base/component rules; keep all selectors)

**Interfaces:**
- Consumes: none. Produces: the new visual theme. No selectors renamed.

- [ ] **Step 1: Replace the `:root` line and base rules at the top of `frontend/styles.css`**

Replace line 1 (`:root {...}`) and the `body`/`#app` rules with:

```css
:root {
  --bg:#0c0a1a; --bg2:#161235; --card:#1b1742; --card2:#241e57;
  --accent:#7c5cff; --accent2:#9b7bff; --gold:#ffd166;
  --good:#2fd27a; --bad:#ff5d6c; --fg:#f3f0ff; --muted:#a79fd6;
}
* { box-sizing: border-box; }
body {
  margin:0; color:var(--fg);
  font-family: system-ui, "Segoe UI", Tahoma, sans-serif;
  background:
    radial-gradient(1200px 600px at 50% -10%, #2a2270 0%, transparent 60%),
    linear-gradient(180deg, var(--bg2) 0%, var(--bg) 60%);
  background-attachment: fixed; min-height:100vh;
}
#app { max-width:560px; margin:0 auto; padding:16px; }
```

- [ ] **Step 2: Restyle the shared button/card/option rules** — replace the existing
`button, .opt {...}`, the accent-button rule, and card rules with:

```css
button, .opt {
  display:block; width:100%; margin:8px 0; padding:14px; border:none; border-radius:14px;
  background:linear-gradient(180deg, var(--card2), var(--card));
  color:var(--fg); font-size:1rem; cursor:pointer; text-align:right;
  box-shadow:0 2px 0 #0006, inset 0 1px 0 #ffffff10; transition:transform .08s ease, filter .15s ease;
}
button:active, .opt:active { transform:translateY(1px) scale(.99); }
.opt.good { background:linear-gradient(180deg,#37e08a,#1faa61); }
.opt.bad { background:linear-gradient(180deg,#ff7480,#d83d4c); }
#btn-board, #btn-home, .quiz-card {
  background:linear-gradient(180deg, var(--accent2), var(--accent));
  text-align:center; font-weight:700; box-shadow:0 4px 16px #7c5cff55, inset 0 1px 0 #ffffff22;
}
.report-item, ol#board-list li, #funfact-text, .badge, .dash-stats .stat, .dash-history li {
  background:linear-gradient(180deg, var(--card2), var(--card));
  box-shadow:inset 0 1px 0 #ffffff10;
}
.summary-big {
  font-size:2.2rem; text-align:center; margin:8px 0; font-weight:800;
  background:linear-gradient(90deg, var(--gold), #fff3c4); -webkit-background-clip:text; background-clip:text; color:transparent;
}
h1, h2 { text-align:center; }
h1 { background:linear-gradient(90deg,var(--accent2),var(--gold)); -webkit-background-clip:text; background-clip:text; color:transparent; }
```

(Leave the match/order/badge/dash structural rules below as-is except where a selector is listed
above; they inherit the new variables. Do not rename selectors.)

- [ ] **Step 3: Verify nothing structural broke — run the full suite**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: vitest 3 (+4 ui) pass; drag e2e passes (selectors unchanged).

- [ ] **Step 4: Visual smoke test** (optional, local)

Run: `cd ../backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --port 8000`
Open `http://localhost:8000/app/` — home, runner, report should show the indigo/gold theme.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css
git commit -m "feat(p1): deep-indigo + gold game theme across screens"
```

---

### Task 3: Motion (keyframes) + fx layer + confetti hooks

**Files:**
- Modify: `frontend/styles.css` (append animations), `frontend/index.html` (fx layer + `ui.js` include), `frontend/app.js` (two guarded hooks)

**Interfaces:**
- Consumes: `window.confetti` / `window.burst` from `ui.js`.
- Produces: animated screen entrance, button pop, correct-answer flash, level-bar keyframe
  (used later in P3), and confetti on correct answers + victory. `app.js` calls are
  `typeof`-guarded.

- [ ] **Step 1: Append animation CSS to `frontend/styles.css`**

```css
/* ---- P1 motion ---- */
.screen { animation: screen-in .28s cubic-bezier(.2,.7,.2,1); }
@keyframes screen-in { from{opacity:0; transform:translateY(14px) scale(.99);} to{opacity:1; transform:none;} }
.opt.correct { animation: pop-good .35s ease; }
@keyframes pop-good { 0%{transform:scale(1);} 40%{transform:scale(1.04);} 100%{transform:scale(1);} }
.opt.wrong { animation: shake .3s ease; }
@keyframes shake { 0%,100%{transform:translateX(0);} 25%{transform:translateX(-5px);} 75%{transform:translateX(5px);} }
#fx-layer { position:fixed; inset:0; pointer-events:none; overflow:hidden; z-index:9999; }
.confetti-piece {
  position:fixed; width:9px; height:9px; border-radius:2px; opacity:.95;
  animation: confetti-fall var(--d,1s) cubic-bezier(.3,.6,.4,1) forwards;
  transform:translateX(calc(var(--x,0) * 40px)) rotate(var(--r,0));
}
@keyframes confetti-fall {
  to { transform:translate(calc(var(--x,0) * 120px), 70vh) rotate(calc(var(--r,0) + 360deg)); opacity:0; }
}
.level-bar { height:10px; border-radius:999px; background:#ffffff1a; overflow:hidden; }
.level-bar > i { display:block; height:100%; background:linear-gradient(90deg,var(--accent2),var(--gold)); transition:width .6s cubic-bezier(.2,.8,.2,1); }
```

- [ ] **Step 2: Edit `frontend/index.html`** — add the fx layer and load `ui.js` before `app.js`.

After the opening `<body>` tag's `<main id="app"> … </main>` (i.e. right before the closing
`</main>` is fine, but simplest just before the app.js script), add the fx layer and script:

```html
  <div id="fx-layer"></div>
  <script src="ui.js?v=p1"></script>
  <script src="app.js?v=3a1"></script>
```

(Replace the existing single `<script src="app.js?v=3a1"></script>` line with the three lines
above. The `?v=` values are auto-restamped by `main.py`.)

- [ ] **Step 3: Edit `frontend/app.js`** — fire confetti on a correct option and on the victory report.

In `pickOption`, inside the correct branch (after `recordAndAdvance(q);`), add a guarded burst:

```javascript
    recordAndAdvance(q);
    if (typeof burst === "function") burst(btn, { count: 10 });
```

In `renderReport`, at the end of the function (after the items loop / before the `btn-board`
handler line), add a guarded confetti for a strong result:

```javascript
  if (typeof confetti === "function" && correct >= Math.ceil(report.items.length / 2)) confetti();
```

(`correct` is already computed at the top of `renderReport`.)

- [ ] **Step 4: Verify — JS still parses and standalone tests pass**

Run:
```bash
cd frontend && node --check app.js && node --check ui.js && npm test && node tests/drag.e2e.mjs
```
Expected: syntax OK; vitest passes (runner.test.js still works because the confetti calls are
`typeof`-guarded and no-op without `ui.js`); drag e2e passes.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css frontend/index.html frontend/app.js
git commit -m "feat(p1): screen/answer animations + confetti hooks + fx layer"
```

---

### Task 4: Full-suite gate + deploy note

**Files:** none (verification task).

- [ ] **Step 1: Run the combined suite**

Run: `./scripts/test.sh`
Expected: backend 106 pass; frontend vitest 7 pass (3 runner + 4 ui); drag e2e passes.

- [ ] **Step 2: Confirm no selector regressions** — grep that the IDs/classes `app.js` relies on still exist in markup/styles:

Run:
```bash
cd frontend && for s in screen-runner q-options order-row chip slot opt quiz-card dash-stats badge; do grep -q "$s" styles.css index.html app.js && echo "ok: $s" || echo "MISSING: $s"; done
```
Expected: `ok:` for every token.

- [ ] **Step 3: Deploy (frontend-only; no reseed/migrate)**

Run: `cd .. && docker compose up -d --build`
Then verify: `curl -s localhost:8000/health` → `{"status":"ok"}`; the served `/app/` shows a new
`?v=` hash; bundle includes the theme (`curl -s localhost:8000/app/styles.css | grep -c gold`).

---

## Self-Review (completed by plan author)

**Spec coverage (P1 slice of §8):** game palette + glows/gradients (Task 2) ✓; CSS animations +
confetti/juice via reusable `ui.js` (Tasks 1, 3) ✓; applied across existing screens without flow
change (selectors preserved, Tasks 2–4) ✓. P2 (map/mentor/onboarding) and P3 (RPG systems) are
out of this plan by design.

**Placeholder scan:** No "TBD/handle later" — every CSS block and JS function is concrete.

**Type consistency:** `confetti(opts)`/`burst(el,opts)` signatures defined in Task 1 match the
calls in Task 3. `#fx-layer` created in Task 3 (index.html) matches `layer()` lookup in Task 1.
The `typeof` guards in Task 3 keep `app.js` evaluable without `ui.js` (required by
`runner.test.js`).

## Out of scope (later phases)
- P2: journey map home, mentor guide, onboarding, `store.js`.
- P3: `game.js` XP/level/rank, HUD, avatar customization, boss reframing, level-up overlay.
