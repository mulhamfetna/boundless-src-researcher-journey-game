# Phase 5 · P5b — Hextech Component Ornamentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the hextech reskin's components — wrap sprites in gold hex-token frames, restyle the map into a glowing "ascension path", refine the HUD/overlays, and add ambient gold ember particles.

**Architecture:** Pure presentation + one reusable `embers()` particle helper in `ui.js` (mirrors `confetti`), mounted ambiently by `renderMap` (guarded). Everything else is CSS over existing selectors; no markup IDs/classes renamed, no logic change.

**Tech Stack:** Dependency-free HTML/CSS/JS; Vitest + jsdom; the `drag.e2e.mjs` browser test.

## Global Constraints

- **Frontend-only.** No backend/API/DB/content/logic change. Preserve every element ID/class.
- **`embers()` call in `app.js` is `typeof`-guarded** so `app.js` evaluates standalone (`runner.test.js` loads it without `ui.js`).
- Hextech palette/fonts from P5a (`--gold #c8aa6e`, `--cyan #0ac8b9`, `--gold-dim #785a28`, `--font-caps` Cinzel). Glows not pixel-shadows.
- **Sprites get gold-ringed token frames** via CSS on their containers (`.node-emoji`, `.hud-avatar`, `.badge .ico`, `.ob-avatar`, `.mentor-avatar`) — the SVG drawings are unchanged.
- **Arabic, RTL.** Keep keyframe names used elsewhere; add new ones namespaced (`ember-rise`, `crystal-pulse`).
- **All existing tests stay green:** `./scripts/test.sh` (pytest 117 + vitest 33 + drag e2e + new embers test).
- Cache-busting already covers `ui.js`/`styles.css` (no `main.py` change). Tests run from `frontend/`.

---

## File Structure

```
frontend/
  ui.js          # MODIFY: add embers(opts) ambient particle helper
  app.js         # MODIFY: renderMap mounts embers() (guarded)
  styles.css     # MODIFY: sprite token frames, ascension-path map, HUD/overlay polish, ember CSS
  tests/ui.test.js  # MODIFY: embers test
```

---

### Task 1: `embers()` ambient particles (TDD)

**Files:** Modify `frontend/ui.js`, `frontend/tests/ui.test.js`

**Interfaces:** Produces `window.embers(opts={}) -> number` — clears any existing `.ember`, then
appends `opts.count` (default 14) `.ember` spans to `#fx-layer` (or `document.body`), each with
randomized CSS custom props; the spans loop via CSS (no auto-removal). Returns the count created.

- [ ] **Step 1: Add the failing test** to `frontend/tests/ui.test.js` (append)

```javascript
describe("embers", () => {
  beforeEach(() => { loadUi(); });
  it("mounts the requested number of embers and is idempotent", () => {
    expect(window.embers({ count: 10 })).toBe(10);
    expect(document.querySelectorAll(".ember").length).toBe(10);
    window.embers({ count: 6 });            // re-mount clears the old ones
    expect(document.querySelectorAll(".ember").length).toBe(6);
  });
  it("defaults to 14 embers", () => {
    expect(window.embers()).toBe(14);
  });
});
```

- [ ] **Step 2: Run, expect fail** — `cd frontend && npm test -- ui` → `window.embers is not a function`.

- [ ] **Step 3: Add `embers` to `frontend/ui.js`** — inside the IIFE, before the exports block:

```javascript
  function embers(opts = {}) {
    const host = document.getElementById("fx-layer") || document.body;
    host.querySelectorAll(".ember").forEach((e) => e.remove());
    const count = opts.count == null ? 14 : opts.count;
    for (let i = 0; i < count; i++) {
      const e = document.createElement("span");
      e.className = "ember";
      e.style.left = Math.floor(Math.random() * 100) + "%";
      e.style.setProperty("--dur", (6 + Math.random() * 6).toFixed(1) + "s");
      e.style.setProperty("--delay", (-Math.random() * 8).toFixed(1) + "s");
      e.style.setProperty("--drift", (Math.random() * 2 - 1).toFixed(2));
      e.style.setProperty("--sz", (2 + Math.random() * 3).toFixed(1) + "px");
      host.appendChild(e);
    }
    return count;
  }
```

And add to the exports block: `window.embers = embers;`

- [ ] **Step 4: Run, expect pass** — `cd frontend && npm test -- ui` → passes.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui.js frontend/tests/ui.test.js
git commit -m "feat(p5b): ambient gold ember particles (embers)"
```

---

### Task 2: Mount embers on the map + ember CSS

**Files:** Modify `frontend/app.js` (renderMap), `frontend/styles.css`

**Interfaces:** Consumes `embers` (guarded). Produces drifting gold motes on the map.

- [ ] **Step 1: Mount embers in `renderMap`** — in `frontend/app.js`, at the end of `renderMap`
(right before `show("home");`), add:

```javascript
  if (typeof embers === "function") embers();
```

- [ ] **Step 2: Append ember CSS** to `frontend/styles.css`:

```css
/* ---- P5b ambient embers ---- */
.ember {
  position:fixed; bottom:-12px; width:var(--sz,3px); height:var(--sz,3px); border-radius:50%;
  background:radial-gradient(circle, #ffe6b0 0%, #c8aa6e 55%, transparent 70%);
  box-shadow:0 0 6px #c8aa6eaa; opacity:0; pointer-events:none;
  animation:ember-rise var(--dur,8s) linear var(--delay,0s) infinite;
}
@keyframes ember-rise {
  0% { transform:translateY(0) translateX(0); opacity:0; }
  10% { opacity:.9; }
  90% { opacity:.6; }
  100% { transform:translateY(-100vh) translateX(calc(var(--drift,0) * 40px)); opacity:0; }
}
```

- [ ] **Step 3: Verify standalone + suite** — `cd frontend && node --check app.js && npm test && node tests/drag.e2e.mjs`
Expected: green (`runner.test.js` unaffected — `embers` call is guarded; not in tested paths).

- [ ] **Step 4: Commit**

```bash
git add frontend/app.js frontend/styles.css
git commit -m "feat(p5b): mount drifting gold embers on the map"
```

---

### Task 3: Sprite gold-token frames + ascension-path map + HUD/overlay polish

**Files:** Modify `frontend/styles.css`

**Interfaces:** Produces gold-ringed sprite tokens, a glowing map path, refined HUD/overlays. CSS only.

- [ ] **Step 1: Append sprite token-frame CSS** to `frontend/styles.css`:

```css
/* ---- P5b hextech sprite tokens ---- */
.node-emoji, .hud-avatar, .badge .ico, .ob-avatar, .mentor-avatar, .levelup-emoji {
  display:inline-flex; align-items:center; justify-content:center;
  background:radial-gradient(circle at 50% 40%, #0a323c 0%, #06101d 70%);
  border:1px solid var(--gold-dim); border-radius:50%;
  box-shadow:0 0 10px #0ac8b933, inset 0 0 8px #00000080; padding:6px;
}
.node-emoji { box-shadow:0 0 12px #c8aa6e44, inset 0 0 8px #000; }
.ob-avatar.selected { border-color:var(--gold); box-shadow:0 0 14px #c8aa6e88; }
.badge.locked .ico { filter:grayscale(1) brightness(.6); }
```

- [ ] **Step 2: Append ascension-path map CSS** to `frontend/styles.css` (restyle the P4c path):

```css
/* ---- P5b ascension path ---- */
.map-path::before { border-left:2px solid #c8aa6e44; box-shadow:0 0 8px #c8aa6e33; }
.map-node { transition:box-shadow .2s ease, border-color .2s ease; }
.map-node:hover { border-color:var(--gold); box-shadow:0 0 16px #c8aa6e55; }
.map-node.next { border-color:var(--gold); box-shadow:0 0 18px #c8aa6e66; animation:crystal-pulse 1.8s ease-in-out infinite; }
.map-node.done { border-color:var(--cyan); box-shadow:0 0 12px #0ac8b944; }
.map-node .node-num { font-family:var(--font-caps); color:var(--gold); opacity:.9; }
.node-mark .sprite { filter:drop-shadow(0 0 4px #c8aa6e88); }
@keyframes crystal-pulse { 0%,100%{ box-shadow:0 0 12px #c8aa6e44; } 50%{ box-shadow:0 0 22px #c8aa6e99; } }
.node-here .sprite { filter:drop-shadow(0 0 6px #0ac8b9aa); }
```

- [ ] **Step 3: Append HUD + overlay polish CSS** to `frontend/styles.css`:

```css
/* ---- P5b HUD + overlay polish ---- */
.map-hud .hud-name { color:var(--gold-bright); font-weight:700; }
.mentor-overlay, .levelup-overlay { background:#010a13cc; backdrop-filter:blur(2px); }
.mentor-card, .levelup-card { box-shadow:0 0 30px #0ac8b933, inset 0 0 0 1px #0a1f33; }
.mentor-next, .levelup-next { background:linear-gradient(180deg,#123,#0a1428); border-color:var(--gold); color:var(--gold-bright); }
.boss-banner, #boss-banner { background:linear-gradient(180deg,#3a0d12,#1a0608); color:var(--gold-bright);
  border:1px solid var(--bad); box-shadow:0 0 14px #ff465555; clip-path:none; }
.report-badge { background:linear-gradient(180deg,#123,#0a1428); border:1px solid var(--gold-dim); color:var(--gold-bright); }
.lb-badge .sprite { vertical-align:middle; }
.passage-text { border-color:var(--gold-dim); background:#04111c; color:#dfe8ff; }
.passage-src a { color:var(--gold); }
```

- [ ] **Step 4: Run the suite** — `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css
git commit -m "feat(p5b): sprite gold tokens, ascension-path map, hextech HUD/overlays"
```

---

### Task 4: Full-suite gate + deploy + screenshot

**Files:** none.

- [ ] **Step 1: Combined suite** — `./scripts/test.sh` → backend 117; frontend vitest 35 (33 + 2 embers); drag e2e.
- [ ] **Step 2: Deploy (frontend-only; no reseed)** — `docker compose up -d --build`; verify
  `curl -s localhost:8000/health` → ok; `curl -s localhost:8000/app/ui.js | grep -c embers` ≥ 1; the
  served bundle carries a fresh `?v=` hash.
- [ ] **Step 3: Screenshot** map + runner + a question; confirm gold sprite tokens, glowing
  ascension path, drifting embers, hextech overlays.

---

## Self-Review (completed by plan author)

**Spec coverage (P5b of §7):** map ascension-path (§4.4) → Task 3; HUD panel + level bar glow (§4.4)
→ Task 3 (+ P5a level bar); overlays as hextech cards (§4.4) → Task 3; sprite gold-hex/token frames
(§4.4) → Task 3; gold ember particles (§4.3) → Tasks 1–2. ✓

**Placeholder scan:** No "TBD" — `embers()` and every CSS block are concrete.

**Type consistency:** `embers(opts)->number` defined in Task 1 matches the guarded call in Task 2 and
its test. New keyframes (`ember-rise`, `crystal-pulse`) are namespaced and don't clash with existing
ones. CSS targets only existing selectors (`.node-emoji`, `.hud-avatar`, `.map-node`, `.mentor-card`,
`#boss-banner`, `.passage-text`, …) — all present from prior phases.

## Out of scope (future)
- Raster/AI Arcane art (no image tool); user may supply later.
