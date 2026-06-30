# رحلة الباحث × Arcane Reskin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Mini App's look to authentically match Arcane — a two-world Zaun↔Piltover climb (shimmer-magenta + acid-green undercity grading up to gold + hextech-cyan Piltover), painterly atmosphere, engraved type, and Arcane-archetype champions — without touching backend/API/DB/content/scoring.

**Architecture:** Frontend-only, dependency-free. A single `--world` scalar (0 = deep Zaun … 1 = high Piltover), derived from the player's level, drives ambient color via `color-mix`. The painterly atmosphere is a CSS/SVG layer stack on `#atmos` (gradient + radial glows + god-rays + grain) plus dual `embers()`. The cast is redrawn as inline-SVG archetypes in `sprites.js`. Screen styling consolidates the contradictory phase-stacked overrides in `styles.css` into one coherent Arcane layer.

**Tech Stack:** Vanilla HTML/CSS/JS, self-hosted woff2 fonts, Vitest + jsdom, puppeteer-core e2e. Telegram Mini App (RTL Arabic).

## Global Constraints

- **Frontend-only.** No change to `backend/`, API, DB, `content/`, or scoring. Preserve every element ID/class in `frontend/index.html`.
- **Dependency-free.** No new libraries. Self-hosted fonts only (already in `frontend/fonts/`).
- **All `app.js` → module calls stay `typeof`-guarded** so `app.js` evaluates standalone (`tests/runner.test.js` loads it without `ui.js`/`game.js`/`sprites.js`).
- **RTL Arabic** throughout; Telegram safe-areas respected.
- **Cache-busting is automatic** — `backend/app/main.py` stamps `styles.css`/`*.js` with a bundle-sha `?v=`. Never hand-edit the `?v=` in `index.html` for the dynamic `/app/` serve. (The static `index.html` literals may stay as-is.)
- **Palette poles (verbatim):** Zaun `--z-shimmer:#ff2e97`, `--z-acid:#2fe6a0`, `--z-violet:#8a3bff`, smog `#14081e`. Piltover `--gold:#c8aa6e`, `--gold-bright:#e2c687`, `--cyan:#0ac8b9`, navy `#0a1428`, ivory `#f0e6d2`. Semantic `--shimmer:#ff2e97`, `--acid:#2fe6a0`, `--bad:#ff4655`, `--good:#0ac8b9`.
- **Fonts:** Aref Ruqaa (titles), Cinzel (caps/numerals), Cairo (body).
- **Full gate:** `./scripts/test.sh` (backend pytest 117 + frontend Vitest + drag e2e) stays green. New JS helpers are TDD'd in `frontend/tests/`.
- **Visual target:** Figma `5vZ86weOps1hxDtG3fqQcg` (Ascension Map).

---

## File Structure

```
frontend/
  game.js     # MODIFY: add worldFromLevel(level) helper (export on window)
  ui.js       # MODIFY: embers() → dual Zaun/Piltover embers, world-aware
  app.js      # MODIFY: renderMap sets --world; embers({world}); boss banner copy
  sprites.js  # MODIFY: Arcane palette + champion/boss/mentor archetypes; AVATAR/STAGE/BADGE maps
  styles.css  # MODIFY: two-world :root tokens; remove contradictory P4a pixel block;
              #         rewrite #atmos (two-world + god-rays + grain); screen restyle
  index.html  # MODIFY (minimal): add god-ray/grain child divs under #atmos if needed
  tests/
    game.test.js     # MODIFY: worldFromLevel tests
    ui.test.js       # MODIFY: dual-ember tests
    sprites.test.js  # MODIFY: new sprite-name tests
```

---

### Task 1: Two-world palette tokens + `worldFromLevel` + override cleanup

Establish the color foundation and the `--world` driver, and remove the leftover pixel-art CSS block (`styles.css:208–228`) and other contradictory overrides that fight the hextech frames.

**Files:**
- Modify: `frontend/game.js` (add `worldFromLevel`)
- Modify: `frontend/styles.css:5-16` (`:root` tokens), delete `styles.css:208-228` (P4a pixel block)
- Modify: `frontend/app.js` (renderMap sets `--world`)
- Test: `frontend/tests/game.test.js`

**Interfaces:**
- Produces: `window.worldFromLevel(level: number) -> number` in `[0,1]` — `0` at level 1, `1` at level ≥ 10, linear between. Consumed by `renderMap` in Task and by `embers` in Task 2.
- Consumes: existing `window.levelFromXp(xp) -> { level, rank_ar, progress, ... }` (unchanged).

- [ ] **Step 1: Write the failing test** — append to `frontend/tests/game.test.js`:

```javascript
describe("worldFromLevel", () => {
  it("is 0 at level 1 (deep Zaun) and 1 at level 10+ (Piltover)", () => {
    expect(window.worldFromLevel(1)).toBe(0);
    expect(window.worldFromLevel(10)).toBe(1);
    expect(window.worldFromLevel(100)).toBe(1);
  });
  it("climbs monotonically in between", () => {
    const a = window.worldFromLevel(3), b = window.worldFromLevel(6);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeGreaterThan(a);
    expect(b).toBeLessThan(1);
  });
  it("clamps below 1", () => { expect(window.worldFromLevel(0)).toBe(0); });
});
```

- [ ] **Step 2: Run, expect fail** — `cd frontend && npm test -- game` → `window.worldFromLevel is not a function`.

- [ ] **Step 3: Implement in `frontend/game.js`** — add before the `window.*` export block:

```javascript
  function worldFromLevel(level) {
    const t = (Number(level) - 1) / 9; // level 1 -> 0, level 10 -> 1
    return Math.max(0, Math.min(1, t));
  }
```

And add to the exports: `window.worldFromLevel = worldFromLevel;`

- [ ] **Step 4: Run, expect pass** — `cd frontend && npm test -- game` → passes.

- [ ] **Step 5: Replace the `:root` token block** — in `frontend/styles.css`, replace lines 5-16 (the current `:root{…}`) with:

```css
:root {
  /* ---- Piltover (mastery / topside) ---- */
  --p-navy:#0a1428; --p-navy-2:#0e1b33; --gold:#c8aa6e; --gold-bright:#e2c687;
  --gold-dim:#785a28; --gold-line:#463714; --cyan:#0ac8b9; --cyan-2:#0397ab;
  --cyan-bright:#cdfafa; --ivory:#f0e6d2;
  /* ---- Zaun (early / undercity) ---- */
  --z-smog:#14081e; --z-smog-2:#1f0f2e; --z-shimmer:#ff2e97; --z-acid:#2fe6a0;
  --z-violet:#8a3bff; --z-ink:#e8d8ff;
  /* ---- semantic ---- */
  --shimmer:#ff2e97; --acid:#2fe6a0; --bad:#ff4655; --good:#0ac8b9;
  --bg:#070310; --panel:#0a1428; --panel2:#0a323c; --ink:#04020a;
  --fg:#f0e6d2; --muted:#a09b8c;
  /* ---- world-lerp: 0 = deep Zaun, 1 = high Piltover (set by app.js) ---- */
  --world:0.15;
  --accent-now: color-mix(in srgb, var(--z-shimmer) calc((1 - var(--world)) * 100%), var(--gold));
  --glow-now:   color-mix(in srgb, var(--z-violet)  calc((1 - var(--world)) * 100%), var(--cyan));
  /* legacy aliases so older rules keep resolving */
  --card:#0a1428; --card2:#0a323c; --accent:#c8aa6e; --accent2:#c8aa6e;
  --pink:#c8aa6e; --teal:#0ac8b9; --bg2:#070310;
  --font-head:"ArefRuqaa","Cairo",serif;
  --font-caps:"Cinzel",serif;
  --font-body:"Cairo",system-ui,"Segoe UI",Tahoma,sans-serif;
  --font-pixel:"Cinzel",serif;
}
```

- [ ] **Step 6: Delete the contradictory pixel-art block** — remove `frontend/styles.css` lines `208-228` entirely (the `/* ---- P4a pixelize remaining components … ---- */` block: `.mentor-card`/`.levelup-card` 3px ink borders, `.level-bar` reset, `.chip`/`.slot`/`.order-row` pixel boxes, `.runner-submit`, `.badge`, `.hint-*`, `#funfact-text`, `.q-image`, `.mchip`, `.report-badge`, `.next-card`, `.dash-*`, `.ob-*`, `.topbar`). These re-impose a chunky retro look that conflicts with the hextech frames. (Leave the P5a/P5b blocks below it intact — Task 4/5 refine them.)

- [ ] **Step 7: Set `--world` in `renderMap`** — in `frontend/app.js`, inside `renderMap`, right after the `currentXp = …` line (≈ line 43) and before the HUD render, add:

```javascript
  if (typeof levelFromXp === "function" && typeof worldFromLevel === "function") {
    const w = worldFromLevel(levelFromXp(currentXp).level);
    document.documentElement.style.setProperty("--world", String(w));
  }
```

- [ ] **Step 8: Verify standalone + suite** — `cd frontend && node --check app.js && node --check game.js && npm test` → all green (runner.test.js unaffected: the new call is `typeof`-guarded).

- [ ] **Step 9: Commit**

```bash
git add frontend/game.js frontend/styles.css frontend/app.js frontend/tests/game.test.js
git commit -m "feat(arcane): two-world palette tokens + worldFromLevel driver; drop pixel-art overrides"
```

---

### Task 2: Two-world atmosphere — `#atmos` + god-rays + grain + dual embers

Replace the single-pole `#atmos` with the painterly two-world stack, and make `embers()` emit Zaun magenta sparks low / Piltover gold motes high, mixed by `--world`.

**Files:**
- Modify: `frontend/styles.css` (`#atmos` block ≈ 180-189, ember CSS ≈ 264-276)
- Modify: `frontend/index.html:11` (add grain/god-ray child layers)
- Modify: `frontend/ui.js` (`embers`)
- Modify: `frontend/app.js` (`renderMap` passes world to `embers`)
- Test: `frontend/tests/ui.test.js`

**Interfaces:**
- Produces: `window.embers(opts={}) -> number`. New optional `opts.world` (0..1, default 0.5). Emits `opts.count` (default 14) spans; `round(count * world)` carry class `ember-pilt` (gold, drift high), the rest `ember-zaun` (magenta, rise from floor). Idempotent (clears prior `.ember`). Returns count.

- [ ] **Step 1: Update the failing tests** — replace the existing `describe("embers", …)` block in `frontend/tests/ui.test.js` with:

```javascript
describe("embers", () => {
  beforeEach(() => { loadUi(); });
  it("mounts count and is idempotent", () => {
    expect(window.embers({ count: 10, world: 0.5 })).toBe(10);
    expect(document.querySelectorAll(".ember").length).toBe(10);
    window.embers({ count: 6, world: 0.5 });
    expect(document.querySelectorAll(".ember").length).toBe(6);
  });
  it("world=1 → all Piltover gold motes", () => {
    window.embers({ count: 8, world: 1 });
    expect(document.querySelectorAll(".ember-pilt").length).toBe(8);
    expect(document.querySelectorAll(".ember-zaun").length).toBe(0);
  });
  it("world=0 → all Zaun shimmer sparks", () => {
    window.embers({ count: 8, world: 0 });
    expect(document.querySelectorAll(".ember-zaun").length).toBe(8);
    expect(document.querySelectorAll(".ember-pilt").length).toBe(0);
  });
  it("defaults to 14 embers", () => { expect(window.embers()).toBe(14); });
});
```

- [ ] **Step 2: Run, expect fail** — `cd frontend && npm test -- ui` → fails (no `.ember-pilt`/`.ember-zaun`).

- [ ] **Step 3: Rewrite `embers` in `frontend/ui.js`** — replace the existing `function embers(opts = {})` body with:

```javascript
  function embers(opts = {}) {
    const host = document.getElementById("fx-layer") || document.body;
    host.querySelectorAll(".ember").forEach((e) => e.remove());
    const count = opts.count == null ? 14 : opts.count;
    const world = opts.world == null ? 0.5 : Math.max(0, Math.min(1, opts.world));
    const gold = Math.round(count * world); // how many Piltover motes
    for (let i = 0; i < count; i++) {
      const e = document.createElement("span");
      e.className = "ember " + (i < gold ? "ember-pilt" : "ember-zaun");
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

- [ ] **Step 4: Run, expect pass** — `cd frontend && npm test -- ui` → passes.

- [ ] **Step 5: Rewrite the `#atmos` block** in `frontend/styles.css` (replace the current `#atmos { … }` ≈ lines 181-189) with the two-world stack:

```css
#atmos {
  position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(120% 70% at 50% -8%, color-mix(in srgb, var(--gold) 30%, transparent) 0%, transparent 55%),
    radial-gradient(70% 45% at 72% 14%, color-mix(in srgb, var(--cyan) 28%, transparent) 0%, transparent 60%),
    radial-gradient(120% 80% at 50% 112%, color-mix(in srgb, var(--z-shimmer) 42%, transparent) 0%, transparent 55%),
    radial-gradient(80% 55% at 30% 96%, color-mix(in srgb, var(--z-acid) 26%, transparent) 0%, transparent 60%),
    radial-gradient(140% 120% at 50% 50%, transparent 50%, #000c 100%),
    linear-gradient(180deg, var(--p-navy) 0%, var(--z-smog-2) 58%, var(--z-smog) 100%);
}
/* god-rays + painterly grain layered above the sky, below content */
#atmos::before {
  content:""; position:absolute; inset:0;
  background:
    repeating-linear-gradient(102deg, transparent 0 38px,
      color-mix(in srgb, var(--gold) 8%, transparent) 38px 42px);
  mix-blend-mode:screen; opacity:.5;
  -webkit-mask-image:linear-gradient(180deg, #000 0%, transparent 46%);
          mask-image:linear-gradient(180deg, #000 0%, transparent 46%);
}
#atmos::after {
  content:""; position:absolute; inset:0; opacity:.05; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)'/></svg>");
}
@media (prefers-reduced-motion: reduce) { .ember { animation:none; opacity:.4; } }
```

- [ ] **Step 6: Add the dual-ember colors** — replace the `.ember { … }` background line in `frontend/styles.css` (≈ 267) so the two variants tint differently. After the existing `.ember { … }` rule, append:

```css
.ember-pilt { background:radial-gradient(circle, #ffe6b0 0%, var(--gold) 55%, transparent 70%); box-shadow:0 0 6px #c8aa6eaa; }
.ember-zaun { background:radial-gradient(circle, #ffd0ec 0%, var(--z-shimmer) 55%, transparent 70%); box-shadow:0 0 7px #ff2e97aa; }
```

(The base `.ember` keeps position/size/animation; the `-pilt`/`-zaun` classes override only the paint.)

- [ ] **Step 7: Pass world to `embers` in `renderMap`** — in `frontend/app.js`, change the guarded `embers()` call (≈ line 73) to:

```javascript
  if (typeof embers === "function") {
    const w = (typeof levelFromXp === "function" && typeof worldFromLevel === "function")
      ? worldFromLevel(levelFromXp(currentXp).level) : 0.4;
    embers({ world: w });
  }
```

- [ ] **Step 8: Verify** — `cd frontend && node --check app.js && npm test && node tests/drag.e2e.mjs` → green (drag e2e may skip without Chrome — acceptable).

- [ ] **Step 9: Screenshot checkpoint** — load the app (`cd backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --reload --port 8000`, open `http://localhost:8000/app/`) and confirm: navy-gold top, magenta-acid smog floor, god-rays raking from upper-left, faint grain, magenta sparks low + gold motes high. (No automated assert — visual gate.)

- [ ] **Step 10: Commit**

```bash
git add frontend/styles.css frontend/ui.js frontend/app.js frontend/tests/ui.test.js
git commit -m "feat(arcane): two-world #atmos (god-rays + grain) + dual Zaun/Piltover embers"
```

---

### Task 3: The cast — Arcane-archetype champions, boss, mentor (sprites.js)

Redraw `sprites.js` in the Arcane palette and replace the generic avatar set with champion archetypes; add boss + mentor sprites. Inline SVG only; no IP likenesses.

**Files:**
- Modify: `frontend/sprites.js`
- Test: `frontend/tests/sprites.test.js`

**Interfaces:**
- Produces: `window.sprite(name)` returns inline `<svg class="sprite" …>` for every name in the maps below; unknown name falls back to the first champion. `window.AVATAR_SPRITES = ["tinkerer","brawler","sniper","alchemist","enforcer","gremlin"]`. `window.STAGE_SPRITES = { foundations:"book", "paper-parts":"puzzle", "paper-types":"doc", journals:"magnifier" }` (unchanged keys). `window.BADGE_SPRITES` keys unchanged. New names available: `tinkerer, brawler, sniper, alchemist, enforcer, gremlin, mentor, boss`.
- Consumes: nothing new. `app.js` already calls `avatarSprite(id)` / `stageSprite(slug)` and falls back safely; mentor uses `sprite("owl")` in `ui.js` — update to `sprite("mentor")`.

- [ ] **Step 1: Update the failing test** — in `frontend/tests/sprites.test.js`, replace the avatar-name assertions with:

```javascript
it("exposes Arcane champion avatars", () => {
  expect(window.AVATAR_SPRITES).toEqual(["tinkerer","brawler","sniper","alchemist","enforcer","gremlin"]);
});
it("renders every champion + boss + mentor as svg", () => {
  for (const n of [...window.AVATAR_SPRITES, "boss", "mentor"]) {
    expect(window.sprite(n)).toContain("<svg");
  }
});
it("falls back to a champion for unknown names", () => {
  expect(window.sprite("nope")).toContain("<svg");
});
it("keeps stage slugs", () => {
  expect(window.STAGE_SPRITES.foundations).toBe("book");
  expect(window.STAGE_SPRITES.journals).toBe("magnifier");
});
```

(Keep any existing badge/stage tests that still hold; delete assertions naming the old `scholar/owl/fox` avatar list.)

- [ ] **Step 2: Run, expect fail** — `cd frontend && npm test -- sprites` → fails on the new avatar list.

- [ ] **Step 3: Rewrite `frontend/sprites.js`** with the Arcane palette and archetypes:

```javascript
(function () {
  // Arcane palette
  const I = "#04020a", GOLD = "#c8aa6e", GOLDH = "#e2c687", CY = "#0ac8b9",
        SH = "#ff2e97", AC = "#2fe6a0", VI = "#8a3bff", IV = "#f0e6d2",
        BR = "#9b6b3a", STL = "#7b8aa6", PNK = "#ff8fc7";
  function svg(body) {
    return `<svg viewBox="0 0 16 16" class="sprite" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
  }
  const r = (x, y, w, h, f) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}"/>`;
  const c = (cx, cy, rr, f) => `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="${f}"/>`;
  const SP = {
    // The Tinkerer — goggled inventor-mentor (brass + gold)
    tinkerer: svg(r(4,3,8,5,IV) + c(6,5,1.1,CY) + c(10,5,1.1,CY) + r(5,4,1,1,I) + r(10,4,1,1,I) + r(4,2,8,1,BR) + r(6,8,4,5,GOLD) + r(5,9,1,3,BR) + r(10,9,1,3,BR)),
    // The Brawler — gauntlets + pink hair-flash
    brawler: svg(r(5,3,6,4,PNK) + r(4,7,8,5,SH) + r(3,8,2,3,GOLD) + r(11,8,2,3,GOLD) + r(6,5,1,1,I) + r(9,5,1,1,I) + r(6,12,4,2,STL)),
    // The Sniper — top-hat + monocle, Piltover blue/gold
    sniper: svg(r(4,1,8,2,I) + r(3,3,10,1,I) + r(5,4,6,5,IV) + c(10,6,1.4,CY) + r(6,6,1,1,I) + r(6,9,4,5,STL) + r(7,10,2,3,GOLD)),
    // The Alchemist — hood + acid vials (Zaun green)
    alchemist: svg(r(5,2,6,5,VI) + r(4,3,8,2,VI) + c(7,5,0.9,AC) + c(9,5,0.9,AC) + r(6,7,4,6,I) + r(7,8,2,4,AC)),
    // The Enforcer — helmet + gold trim
    enforcer: svg(r(4,3,8,5,STL) + r(4,3,8,1,GOLD) + r(6,6,4,1,CY) + r(5,8,6,5,STL) + r(7,9,2,3,GOLD)),
    // The Gremlin — chaos boss, magenta sparks
    gremlin: svg(r(5,4,6,5,SH) + r(4,2,2,2,VI) + r(10,2,2,2,VI) + r(6,6,1,1,I) + r(9,6,1,1,I) + r(6,9,4,1,GOLDH) + r(4,11,8,2,SH) + r(3,12,1,1,AC) + r(12,12,1,1,AC)),
    // mentor = tinkerer alias for the guide overlay; boss = gremlin for surges
    book: svg(r(3,3,5,10,SH) + r(8,3,5,10,CY) + r(7,3,2,10,I) + r(4,5,3,1,IV) + r(9,5,3,1,IV)),
    puzzle: svg(r(3,3,6,6,CY) + r(8,7,5,6,GOLD) + r(9,5,2,2,GOLD) + r(6,8,2,2,CY)),
    doc: svg(r(4,2,8,12,IV) + r(5,4,6,1,I) + r(5,6,6,1,I) + r(5,8,6,1,I) + r(5,10,4,1,I) + r(10,2,2,2,GOLD)),
    magnifier: svg(r(4,3,6,6,IV) + r(5,4,4,4,CY) + r(3,3,7,1,I) + r(3,9,7,1,I) + r(3,4,1,5,I) + r(9,4,1,5,I) + r(10,10,3,3,GOLD)),
    crown: svg(r(3,8,10,4,GOLD) + r(3,4,2,4,GOLD) + r(7,4,2,4,GOLD) + r(11,4,2,4,GOLD) + r(3,4,2,2,CY) + r(11,4,2,2,CY) + r(7,4,2,2,CY)),
    star: svg(r(7,2,2,12,GOLD) + r(2,7,12,2,GOLD) + r(4,4,8,8,GOLD) + r(6,6,4,4,IV)),
    check: svg(r(11,4,2,2,CY) + r(9,6,2,2,CY) + r(7,8,2,2,CY) + r(5,7,2,2,CY) + r(3,6,2,2,CY) + r(5,9,2,2,CY)),
    flag: svg(r(4,2,1,12,I) + r(5,3,7,5,SH) + r(5,3,7,1,I) + r(11,3,1,5,I)),
    perfect_quiz: svg(r(5,2,6,6,GOLD) + r(6,3,4,4,IV) + r(5,8,2,5,SH) + r(9,8,2,5,SH) + r(6,13,4,1,I)),
    self_reliant: svg(r(4,2,8,3,CY) + r(3,4,10,5,CY) + r(5,9,6,4,CY) + r(7,5,2,5,IV)),
    streak_master: svg(r(7,2,2,2,GOLD) + r(6,4,4,3,SH) + r(5,7,6,4,SH) + r(6,11,4,2,GOLD) + r(7,5,2,5,GOLD)),
    first_finish: svg(r(7,2,2,12,GOLD) + r(2,7,12,2,GOLD) + r(4,4,8,8,GOLD)),
    bug: svg(r(6,2,4,3,SH) + r(4,5,8,6,SH) + r(5,11,6,2,SH) + r(6,6,1,1,I) + r(9,6,1,1,I) + r(3,6,2,1,I) + r(11,6,2,1,I) + r(3,9,2,1,I) + r(11,9,2,1,I) + r(7,5,2,7,I)),
  };
  SP.mentor = SP.tinkerer;
  SP.boss = SP.gremlin;
  function sprite(name) { return SP[name] || SP.tinkerer; }
  window.sprite = sprite;
  window.AVATAR_SPRITES = ["tinkerer", "brawler", "sniper", "alchemist", "enforcer", "gremlin"];
  window.STAGE_SPRITES = { foundations: "book", "paper-parts": "puzzle", "paper-types": "doc", journals: "magnifier" };
  window.BADGE_SPRITES = { perfect_quiz: "perfect_quiz", self_reliant: "self_reliant", streak_master: "streak_master", first_finish: "first_finish" };
})();
```

- [ ] **Step 4: Point the mentor overlay at the new sprite** — in `frontend/ui.js`, in `mentorSay`, change `sprite("owl")` to `sprite("mentor")` (keep the `typeof sprite === "function"` guard and the `🦉` fallback).

- [ ] **Step 5: Run, expect pass** — `cd frontend && npm test -- sprites && npm test -- ui` → green.

- [ ] **Step 6: Default-avatar safety** — confirm `app.js` `avatarSprite` falls back when a stored profile has an old avatar id (`scholar`): it already does (`AVATAR_SPRITES.includes(id) ? id : "scholar"`). Change the fallback string `"scholar"` → `"tinkerer"` in both `avatarSprite` (≈ line 28) and the `AVATARS` const (≈ line 26) so legacy profiles render a valid champion.

- [ ] **Step 7: Verify standalone + suite** — `cd frontend && node --check app.js && node --check sprites.js && npm test` → green.

- [ ] **Step 8: Commit**

```bash
git add frontend/sprites.js frontend/ui.js frontend/app.js frontend/tests/sprites.test.js
git commit -m "feat(arcane): champion archetypes (tinkerer/brawler/sniper/alchemist/enforcer/gremlin) + boss/mentor sprites"
```

---

### Task 4: Signature screens — Ascension Map + Runner/Boss

Restyle the two screens that carry the brand, to match the Figma target. CSS-only on existing selectors; consolidates the P4c/P5b map rules and the runner/boss rules.

**Files:**
- Modify: `frontend/styles.css` (map section ≈ 251-262 + 289-298; runner/boss ≈ 168-170, 305-306)
- Test: visual + existing `npm test` green

**Interfaces:** Consumes Tasks 1-3 tokens (`--world`, `--accent-now`, `--glow-now`, `--shimmer`) and sprite tokens. No JS/markup change.

- [ ] **Step 1: Restyle the ascension path + nodes** — append to `frontend/styles.css`:

```css
/* ---- Arcane signature: map ---- */
.map-path::before { border-left:2px dashed color-mix(in srgb, var(--gold) 40%, transparent);
  box-shadow:0 0 8px #c8aa6e33; }
.map-node { background:linear-gradient(180deg, color-mix(in srgb,var(--z-smog-2) 70%, var(--p-navy)) , #06101dee);
  border:1px solid var(--gold-dim); }
.map-node.done { border-color:var(--shimmer); box-shadow:0 0 12px #ff2e9744; }
.map-node.done .node-mark { color:var(--shimmer); }
.map-node.next { border-color:var(--cyan); box-shadow:0 0 18px #0ac8b966; animation:crystal-pulse 1.8s ease-in-out infinite; }
.map-node .node-num { font-family:var(--font-caps); color:var(--gold-bright); }
.node-here .sprite { filter:drop-shadow(0 0 6px var(--cyan)); }
@keyframes crystal-pulse { 0%,100%{ box-shadow:0 0 12px #0ac8b944; } 50%{ box-shadow:0 0 22px #0ac8b999; } }
.map-hud { background:linear-gradient(180deg,#0e1b33f2,#0a1428f2); border:1px solid var(--gold-dim);
  box-shadow:0 3px 10px #0008; }
.map-hud .hud-name { color:var(--gold-bright); }
.map-hud .hud-rank { color:var(--cyan); font-family:var(--font-caps); }
```

- [ ] **Step 2: Restyle the runner field + boss surge banner** — append:

```css
/* ---- Arcane signature: runner + boss surge ---- */
#screen-runner h2#q-prompt { color:var(--gold-bright); }
#boss-banner { text-align:center; font-family:var(--font-caps); letter-spacing:2px; font-weight:800;
  color:#ffd7da; padding:10px; margin-bottom:10px; clip-path:none;
  background:linear-gradient(180deg,#3a0d22,#14081e); border:1px solid var(--shimmer);
  box-shadow:0 0 16px #ff2e9766; animation:pop-good .4s ease; }
#screen-runner.boss .opt { border-color:color-mix(in srgb,var(--shimmer) 60%, var(--gold-dim)); }
#screen-runner.boss .opt:hover { box-shadow:0 0 14px #ff2e9755, inset 0 0 18px #8a3bff22; }
.opt.good, .opt.correct { border-color:var(--cyan); color:var(--cyan-bright); box-shadow:0 0 16px #0ac8b966; }
.opt.bad, .opt.wrong { border-color:var(--shimmer); color:#ffd7da; box-shadow:0 0 16px #ff2e9766; background:linear-gradient(180deg,#1a0610ee,#06101dee); }
```

- [ ] **Step 3: Update boss-banner copy to the "shimmer surge"** — in `frontend/app.js`, find where the boss banner text is set (the `#boss-banner` content in `startQuiz`/`renderQuestion`) and set its label to include `موجة الشيمر` (shimmer surge), e.g. `bossBanner.textContent = "⚡ موجة الشيمر — السؤال الأقوى";`. Keep the existing show/hide logic and the `screen-runner.boss` class toggle.

- [ ] **Step 4: Verify** — `cd frontend && node --check app.js && npm test && node tests/drag.e2e.mjs` → green.

- [ ] **Step 5: Screenshot checkpoint** — confirm the map matches the Figma target (climbing trail, tiered glow-nodes: magenta done → cyan next, HUD panel, embers) and the runner shows the magenta shimmer-surge banner on the boss question with gold-rim options flashing cyan/magenta.

- [ ] **Step 6: Commit**

```bash
git add frontend/styles.css frontend/app.js
git commit -m "feat(arcane): ascension-map + runner/boss shimmer-surge signature screens"
```

---

### Task 5: Remaining screens — funfact, report, board, badges, onboarding

Bring the secondary screens onto the Arcane system; report tints by score via `--world`.

**Files:**
- Modify: `frontend/styles.css` (funfact ≈ 87-88/220, report items 44-54, badges 72-77, onboarding 159-162, dash blocks)
- Modify: `frontend/app.js` (report screen sets a local `--world` from score)
- Test: visual + `npm test` green (incl. `tests/report_ui.test.js`, `tests/passage_ui.test.js`)

**Interfaces:** Consumes Task 1 tokens. `showReport`/`renderReport` in `app.js` gains a `--world` set from accuracy.

- [ ] **Step 1: Tint the report by score** — in `frontend/app.js`, where the report renders (after computing `report.accuracy` or the summary), add:

```javascript
  if (typeof report.accuracy === "number") {
    document.documentElement.style.setProperty("--world", String(Math.max(0, Math.min(1, report.accuracy))));
  }
```

(High accuracy → Piltover gold ascension; low → Zaun. Guarded by the `typeof`.)

- [ ] **Step 2: Restyle secondary screens** — append to `frontend/styles.css`:

```css
/* ---- Arcane: secondary screens ---- */
#funfact-text { background:linear-gradient(180deg,#0e1b33ee,#06101dee); border:1px solid var(--cyan-2);
  box-shadow:0 0 18px #0ac8b933; border-radius:0;
  clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px); }
.report-item { background:linear-gradient(180deg,#0a1428dd,#06101ddd); border:1px solid var(--gold-dim); }
.report-item.good { border-right:4px solid var(--cyan); }
.report-item.bad { border-right:4px solid var(--shimmer); }
.summary-big { color:var(--accent-now); text-shadow:0 0 14px var(--glow-now); }
.badge { background:linear-gradient(180deg,#0e1b33dd,#06101ddd); border:1px solid var(--gold-dim); border-radius:0;
  clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px); }
.badge.locked { opacity:.45; filter:grayscale(1) brightness(.6); }
.next-card { background:linear-gradient(180deg,#123,#0a1428); border:1px solid var(--gold-dim); color:var(--gold-bright);
  border-radius:0; }
ol#board-list li { background:linear-gradient(180deg,#0a1428dd,#06101ddd); border:1px solid var(--gold-dim); border-radius:0; }
.ob-name { background:#06101d; border:1px solid var(--gold-dim); color:var(--ivory); border-radius:0; }
.ob-avatar { background:radial-gradient(circle at 50% 40%, #0a323c, #06101d); border:1px solid var(--gold-dim); border-radius:50%; }
.ob-avatar.selected { border-color:var(--cyan); box-shadow:0 0 14px #0ac8b988; }
.mchip.lv-mastered { background:var(--cyan); color:var(--ink); }
.mchip.lv-proficient { background:var(--gold); color:var(--ink); }
.mchip.lv-familiar { background:var(--z-violet); color:#fff; }
```

- [ ] **Step 3: Verify** — `cd frontend && node --check app.js && npm test` → green (report_ui/passage_ui unaffected — class names preserved).

- [ ] **Step 4: Screenshot checkpoint** — confirm funfact (cyan crystal card), report (score-tinted, magenta/cyan item rails), badges (gold-token, locked = undercity gray), onboarding (champion picker as gold-ring tokens).

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css frontend/app.js
git commit -m "feat(arcane): funfact/report/board/badges/onboarding on the two-world system (report tints by score)"
```

---

### Task 6: Full-suite gate + deploy + screenshot parity

**Files:** none.

- [ ] **Step 1: Full suite** — from repo root: `./scripts/test.sh` → backend pytest 117 green; frontend Vitest green (incl. updated game/ui/sprites tests); drag e2e green or cleanly skipped.

- [ ] **Step 2: Deploy (frontend-only; no reseed, no migrate)** — `docker compose up -d --build`; then verify:
  - `curl -s localhost:8000/health` → ok
  - `curl -s localhost:8000/app/sprites.js | grep -c tinkerer` ≥ 1
  - `curl -s localhost:8000/app/styles.css | grep -c -- "--world"` ≥ 1
  - the served `index.html` carries a fresh `?v=` bundle hash (auto-stamped).

- [ ] **Step 3: Screenshot parity** — capture map + runner(boss) + report; compare against the Figma target (`5vZ86weOps1hxDtG3fqQcg`). Confirm: two-world gradient, dashed climbing trail, tiered glow-nodes, dual embers, shimmer-surge banner, champion tokens. Note any residual chunky/flat areas and fix in a follow-up commit.

- [ ] **Step 4: Update memory** — update `telegram-quiz-project.md` + `MEMORY.md` index: Phase 6 Arcane two-world reskin done & live.

---

## Self-Review (completed by plan author)

**Spec coverage:**
- §2 metaphor (Zaun→Piltover climb) → Task 1 `--world` + Task 4 map. ✓
- §3 two-pole palette + `--world` lerp + legacy aliases → Task 1. ✓
- §4 typography (Aref Ruqaa/Cinzel/Cairo) → already loaded; titles/numerals styled across Tasks 4-5; `--font-*` retained in Task 1 `:root`. ✓
- §5 atmosphere (#atmos, god-rays, grain, bloom, dual embers) → Task 2. ✓
- §6 cast archetypes (tinkerer/brawler/sniper/gremlin/alchemist + enforcer) + avatar picker → Task 3 (+ onboarding tokens Task 5). ✓
- §7 per-screen treatment → Task 4 (map, runner/boss) + Task 5 (funfact, report, board, badges, onboarding). ✓
- §8 motion (crystal-pulse, embers, god-ray, reduced-motion) → Task 2 (reduced-motion) + Task 4 (crystal-pulse). ✓
- §9 constraints (frontend-only, guards, RTL, cache-bust, tests) → Global Constraints + per-task verify steps. ✓
- §11 decomposition (foundation/atmosphere/cast/screens/gate) → Tasks 1-6. ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to". Every CSS/JS block is concrete.

**Type consistency:** `worldFromLevel(level)->number` defined in Task 1 is used identically in Tasks 2 (embers world) and reused for report tint in Task 5. `embers(opts.world)` signature in Task 2 matches its test and the `renderMap` call. Sprite names in Task 3 (`tinkerer…gremlin`, `boss`, `mentor`) match `AVATAR_SPRITES`, the `ui.js` `mentor` reference (Task 3 Step 4), and the `avatarSprite` fallback rename (Task 3 Step 6). New keyframe `crystal-pulse` is redefined once in Task 4 (replacing the P5b one — same name, intended). `--accent-now`/`--glow-now` defined in Task 1 are consumed in Task 5 `.summary-big`.

**Note for executor:** Tasks 4-5 append CSS that intentionally overrides earlier P5a/P5b rules of the same selector (cascade order). Do not delete the P5a/P5b blocks; the appended Arcane rules win by source order. Only the P4a pixel block (Task 1 Step 6) is removed outright.
