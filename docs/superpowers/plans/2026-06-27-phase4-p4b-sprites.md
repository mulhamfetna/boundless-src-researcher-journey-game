# Phase 4 · P4b — SVG Pixel Sprites (replace all emoji) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every emoji (avatars, stage icons, badges, mentor, boss crown, marks) with hand-authored inline SVG pixel sprites, removing the biggest remaining "AI-generated" tell.

**Architecture:** New `frontend/sprites.js` exposes `window.sprite(name)` → an inline SVG string (flat, `shape-rendering:crispEdges`, arcade palette, ink outlines) plus the id maps. `app.js` swaps emoji literals for `sprite(...)` calls (`typeof`-guarded). Profile `avatar` becomes a sprite id with back-compat for old emoji values. Frontend-only.

**Tech Stack:** Dependency-free HTML/CSS/JS; Vitest + jsdom; drag-e2e.

## Global Constraints

- **Frontend-only.** No backend/API/DB/content/logic change except adding `sprites.js` to `main.py` cache-busting.
- **Guard all `sprite(...)` calls in `app.js` with `typeof sprite === "function"`** so `app.js` evaluates standalone (`runner.test.js` loads it without `sprites.js`).
- Sprites: `<svg viewBox="0 0 16 16" class="sprite" shape-rendering="crispEdges">…</svg>`; flat fills from the arcade palette; sized by CSS (`.sprite{width:1.6em;height:1.6em;vertical-align:middle}`).
- **Avatar back-compat:** stored `avatar` may be an old emoji; if it isn't a known sprite id, render the `scholar` sprite.
- Preserve all element IDs/classes; Arabic/RTL.
- Script load order: `store.js, game.js, sprites.js, ui.js, app.js`.
- **All existing tests stay green:** `./scripts/test.sh` (pytest 106 + vitest 28 + drag e2e + new sprite tests).

## File Structure

```
frontend/
  sprites.js          # CREATE: sprite(name) + AVATAR_SPRITES/STAGE_SPRITES/BADGE_SPRITES
  styles.css          # MODIFY: .sprite sizing; sprite slots in hud/map/badges
  index.html          # MODIFY: include sprites.js before ui.js/app.js
  app.js              # MODIFY: emoji -> sprite() at every render site
  tests/sprites.test.js   # CREATE
backend/app/main.py   # MODIFY: cache-bust list += sprites.js
```

---

### Task 1: `sprites.js` (TDD)

**Files:** Create `frontend/sprites.js`, `frontend/tests/sprites.test.js`

**Interfaces:**
- `window.sprite(name) -> string` — non-empty `<svg…>` for a known id; falls back to the `scholar`
  sprite for unknown ids.
- `window.AVATAR_SPRITES: string[]` (ids), `STAGE_SPRITES: {slug:id}`, `BADGE_SPRITES: {code:id}`.

- [ ] **Step 1: Failing tests** — `frontend/tests/sprites.test.js`

```javascript
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "sprites.js"), "utf8");
beforeEach(() => { new Function("window", src)(window); });

describe("sprites", () => {
  it("returns an svg for known ids", () => {
    for (const id of ["scholar", "owl", "book", "magnifier", "crown", "star", "check"]) {
      expect(window.sprite(id)).toMatch(/^<svg/);
    }
  });
  it("falls back to scholar for unknown ids", () => {
    expect(window.sprite("zzz")).toBe(window.sprite("scholar"));
  });
  it("exposes the id maps with expected keys", () => {
    expect(window.AVATAR_SPRITES.length).toBeGreaterThanOrEqual(6);
    expect(Object.keys(window.STAGE_SPRITES).sort()).toEqual(["foundations", "journals", "paper-parts", "paper-types"]);
    expect(Object.keys(window.BADGE_SPRITES).sort()).toEqual(["first_finish", "perfect_quiz", "self_reliant", "streak_master"]);
  });
});
```

- [ ] **Step 2: Run, expect fail** — `cd frontend && npm test -- sprites` → cannot read `../sprites.js`.

- [ ] **Step 3: Create `frontend/sprites.js`** (compact flat pixel icons; ink outline `#06101f`)

```javascript
(function () {
  const I = "#06101f", P = "#ff5277", G = "#ffd23f", T = "#2ec4b6", W = "#eaf2ff", S = "#9fb3d6", B = "#7c5cff", BR = "#b5651d";
  function svg(body) {
    return `<svg viewBox="0 0 16 16" class="sprite" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
  }
  const r = (x, y, w, h, f) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}"/>`;
  const SP = {
    scholar: svg(r(4,2,8,2,I) + r(3,3,10,1,I) + r(5,4,6,5,G) + r(6,9,4,4,T) + r(5,13,6,1,I)), // grad cap + face + gown
    scientist: svg(r(5,3,6,5,W) + r(6,2,4,1,I) + r(6,8,4,5,T) + r(5,9,1,3,W) + r(10,9,1,3,W)), // goggles head + coat
    coder: svg(r(4,3,8,5,S) + r(5,8,6,5,B) + r(6,5,1,1,I) + r(9,5,1,1,I) + r(5,11,6,1,W)), // head + hoodie + laptop bar
    owl: svg(r(4,3,8,8,BR) + r(5,5,2,2,W) + r(9,5,2,2,W) + r(6,6,1,1,I) + r(10,6,1,1,I) + r(7,7,2,2,G) + r(5,11,6,2,BR) + r(6,2,1,1,BR) + r(9,2,1,1,BR)),
    fox: svg(r(4,5,8,6,P) + r(3,3,3,3,P) + r(10,3,3,3,P) + r(6,7,1,1,I) + r(9,7,1,1,I) + r(7,9,2,1,I) + r(6,5,4,2,W)),
    cat: svg(r(4,5,8,6,S) + r(4,3,2,3,S) + r(10,3,2,3,S) + r(6,7,1,1,I) + r(9,7,1,1,I) + r(7,9,2,1,P)),
    book: svg(r(3,3,5,10,P) + r(8,3,5,10,T) + r(7,3,2,10,I) + r(4,5,3,1,W) + r(9,5,3,1,W)),
    puzzle: svg(r(3,3,6,6,T) + r(8,7,5,6,G) + r(9,5,2,2,G) + r(6,8,2,2,T)),
    doc: svg(r(4,2,8,12,W) + r(5,4,6,1,I) + r(5,6,6,1,I) + r(5,8,6,1,I) + r(5,10,4,1,I) + r(10,2,2,2,S)),
    magnifier: svg(r(4,3,6,6,W) + r(5,4,4,4,T) + r(3,3,7,1,I) + r(3,9,7,1,I) + r(3,4,1,5,I) + r(9,4,1,5,I) + r(10,10,3,3,I)),
    crown: svg(r(3,8,10,4,G) + r(3,4,2,4,G) + r(7,4,2,4,G) + r(11,4,2,4,G) + r(3,4,2,2,P) + r(11,4,2,2,P) + r(7,4,2,2,P)),
    star: svg(r(7,2,2,12,G) + r(2,7,12,2,G) + r(4,4,8,8,G) + r(6,6,4,4,W)),
    check: svg(r(11,4,2,2,T) + r(9,6,2,2,T) + r(7,8,2,2,T) + r(5,7,2,2,T) + r(3,6,2,2,T) + r(5,9,2,2,T)),
    flag: svg(r(4,2,1,12,I) + r(5,3,7,5,P) + r(5,3,7,1,I) + r(11,3,1,5,I)),
    perfect_quiz: svg(r(5,2,6,6,G) + r(6,3,4,4,W) + r(5,8,2,5,P) + r(9,8,2,5,P) + r(6,13,4,1,I)), // medal
    self_reliant: svg(r(4,2,8,3,T) + r(3,4,10,5,T) + r(5,9,6,4,T) + r(7,5,2,5,W)), // shield
    streak_master: svg(r(7,2,2,2,G) + r(6,4,4,3,P) + r(5,7,6,4,P) + r(6,11,4,2,G) + r(7,5,2,5,G)), // flame
    first_finish: svg(r(7,2,2,12,G) + r(2,7,12,2,G) + r(4,4,8,8,G)), // simple star/spark
  };
  function sprite(name) { return SP[name] || SP.scholar; }
  window.sprite = sprite;
  window.AVATAR_SPRITES = ["scholar", "scientist", "coder", "owl", "fox", "cat"];
  window.STAGE_SPRITES = { foundations: "book", "paper-parts": "puzzle", "paper-types": "doc", journals: "magnifier" };
  window.BADGE_SPRITES = { perfect_quiz: "perfect_quiz", self_reliant: "self_reliant", streak_master: "streak_master", first_finish: "first_finish" };
})();
```

- [ ] **Step 4: Run, expect pass** — `cd frontend && npm test -- sprites` → 3 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/sprites.js frontend/tests/sprites.test.js
git commit -m "feat(p4b): SVG pixel sprite set (sprites.js)"
```

---

### Task 2: Wire sprites in (CSS, index.html, main.py cache-bust)

**Files:** Modify `frontend/styles.css`, `frontend/index.html`, `backend/app/main.py`

- [ ] **Step 1: `.sprite` sizing** — append to `frontend/styles.css`:

```css
/* ---- P4b sprites ---- */
.sprite { width:1.6em; height:1.6em; vertical-align:middle; display:inline-block; }
.hud-avatar .sprite { width:2.2em; height:2.2em; }
.map-node .node-emoji .sprite, .map-node .sprite { width:2em; height:2em; }
.badge .ico .sprite { width:2.4em; height:2.4em; }
.ob-avatar .sprite { width:2em; height:2em; }
.mentor-avatar .sprite { width:2.6em; height:2.6em; }
```

- [ ] **Step 2: Include `sprites.js`** in `frontend/index.html` (before `ui.js`):

```html
  <script src="store.js?v=p2"></script>
  <script src="game.js?v=p2"></script>
  <script src="sprites.js?v=p4b"></script>
  <script src="ui.js?v=p2"></script>
  <script src="app.js?v=3a1"></script>
```

- [ ] **Step 3: Cache-bust `sprites.js`** — in `backend/app/main.py`, extend both the hash list and
the regex:

```python
    for fn in ("app.js", "ui.js", "store.js", "game.js", "sprites.js", "styles.css"):
```
```python
            r"(app\.js|ui\.js|store\.js|game\.js|sprites\.js|styles\.css)\?v=[A-Za-z0-9_]+",
```

- [ ] **Step 4: Backend suite** — `cd backend && pytest -q` → 106 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css frontend/index.html backend/app/main.py
git commit -m "feat(p4b): wire sprites (css sizing, include, cache-bust)"
```

---

### Task 3: Swap emoji → sprites in `app.js`

**Files:** Modify `frontend/app.js`

**Interfaces:** Consumes `sprite`, `AVATAR_SPRITES`, `STAGE_SPRITES`, `BADGE_SPRITES` (guarded).

- [ ] **Step 1: Replace the emoji constants + helper.** In `frontend/app.js`, replace the
`STAGE_EMOJI` and `AVATARS` declarations with sprite-backed versions and add a guarded helper:

```javascript
const AVATARS = (typeof AVATAR_SPRITES !== "undefined") ? AVATAR_SPRITES : ["scholar", "owl", "fox"];
function spr(name) { return (typeof sprite === "function") ? sprite(name) : ""; }
function avatarSprite(id) { return spr((typeof AVATAR_SPRITES !== "undefined" && AVATAR_SPRITES.includes(id)) ? id : "scholar"); }
function stageSprite(slug) { return spr((typeof STAGE_SPRITES !== "undefined" && STAGE_SPRITES[slug]) || "book"); }
```

(Delete the old `const STAGE_EMOJI = {…}` line.)

- [ ] **Step 2: Map node icon** — in `renderMap`, replace the node-emoji span and mark:

```javascript
    const mark = s.status === "done" ? spr("check") : (s.status === "next" ? spr("star") : "");
    node.innerHTML =
      `<span class="node-emoji">${stageSprite(s.slug)}</span>` +
      `<span class="node-title">${s.title_ar}</span>` +
      `<span class="node-mark">${mark}</span>`;
```

- [ ] **Step 3: HUD avatar** — in `renderMap`, the `renderHUD` call already passes `profile.avatar`;
change `renderHUD` usage to pass the sprite. Replace the `renderHUD(hud, {...})` call's `avatar`
field and the fallback:

```javascript
    renderHUD(hud, { avatar: avatarSprite(profile.avatar), name: profile.name, rank_ar: lv.rank_ar, level: lv.level, progress: lv.progress });
    const av = hud.querySelector(".hud-avatar");
    if (av) av.onclick = () => openAvatarPicker(profile);
  } else {
    hud.innerHTML = `<span class="hud-avatar">${avatarSprite(profile.avatar)}</span><span class="hud-name">${profile.name || "باحث"}</span>`;
```

(Note: `renderHUD` in `ui.js` inserts `s.avatar` as HTML inside `.hud-avatar` — an SVG string is
valid there.)

- [ ] **Step 4: Onboarding + avatar picker** — in `showOnboarding`, render sprites in the grid and
the mentor; in `openAvatarPicker` likewise:

In `showOnboarding`, replace the mentor line and the avatar button content:

```javascript
  mentor.innerHTML =
    `<div class="mentor-card"><div class="mentor-avatar">${spr("owl")}</div>` +
    `<div class="mentor-text">${mentorLineFor("welcome_anon", {})}</div></div>`;
```
```javascript
    b.className = "ob-avatar" + (i === 0 ? " selected" : "");
    b.innerHTML = avatarSprite(a);
```
and set the default chosen + selection compare by id (they already are ids from `AVATARS`).

In `openAvatarPicker`, replace `b.textContent = a;` with `b.innerHTML = avatarSprite(a);` and keep
`a === profile.avatar` selection.

- [ ] **Step 5: Mentor bubble owl** — the `mentorSay` overlay (in `ui.js`) hardcodes `🦉`. In
`enterStage`, pass nothing extra (mentorSay owns its avatar). Update `ui.js` `mentorSay` to use a
guarded sprite: replace `'<div class="mentor-avatar">🦉</div>'` with
`'<div class="mentor-avatar">' + (typeof sprite === "function" ? sprite("owl") : "🦉") + '</div>'`.

- [ ] **Step 6: Badges (BADGES map)** — replace the emoji `ico` in the `BADGES` object with sprite
ids, and render via `spr`. Change the `BADGES` declaration:

```javascript
const BADGES = {
  perfect_quiz: { ico: "perfect_quiz", name_ar: "الإتقان" },
  self_reliant: { ico: "self_reliant", name_ar: "بلا تلميحات" },
  streak_master: { ico: "streak_master", name_ar: "السلسلة" },
  first_finish: { ico: "first_finish", name_ar: "البداية" },
};
```

Then at each render of `b.ico` (in `loadBadges`, `renderReport` report-badges, `loadBoard`
top-badge), wrap with `spr(...)`:
- `loadBadges`: `div.innerHTML = `<div class="ico">${spr(b.ico)}</div><div>${b.name_ar}</div>`;`
- `renderReport` badge chip: `span.innerHTML = `${spr(b.ico)} ${b.name_ar}`;` (use innerHTML not textContent)
- `loadBoard` top-badge: ``const badge = (r.top_badge && BADGES[r.top_badge]) ? `<span class="lb-badge">${spr(BADGES[r.top_badge].ico)}</span>` : "";``

- [ ] **Step 7: Boss crown + hint** — the boss banner text is in `index.html` (`👑 تحدّي الزعيم`).
Replace it in `index.html` with a sprite slot filled at render. Simplest: in `renderQuestion`, when
`isBoss`, set the banner HTML:

```javascript
  if (bossBanner) {
    bossBanner.classList.toggle("hidden", !isBoss);
    if (isBoss) bossBanner.innerHTML = `${spr("crown")} تحدّي الزعيم`;
  }
```

And change the static `index.html` banner to empty: `<div id="boss-banner" class="hidden"></div>`.

- [ ] **Step 8: Level-up star** — `ui.js` `levelUpOverlay` hardcodes `⭐`; replace with guarded
sprite: `'<div class="levelup-emoji">' + (typeof sprite === "function" ? sprite("star") : "⭐") + '</div>'`.

- [ ] **Step 9: Verify standalone + suite**

Run: `cd frontend && node --check app.js && node --check sprites.js && node --check ui.js && npm test && node tests/drag.e2e.mjs`
Expected: syntax OK; vitest passes (sprite calls guarded; `runner.test.js` loads `app.js`/`ui.js`
without `sprites.js`, so `spr`/`sprite` no-op to `""`); drag e2e passes.

- [ ] **Step 10: Commit**

```bash
git add frontend/app.js frontend/ui.js frontend/index.html
git commit -m "feat(p4b): replace all emoji with SVG sprites across screens"
```

---

### Task 4: Full-suite gate + deploy + screenshot

- [ ] **Step 1: Combined suite** — `./scripts/test.sh` → backend 106; vitest 31 (28 + 3 sprites); drag e2e.
- [ ] **Step 2: Deploy** — `docker compose up -d --build`; verify `curl -s localhost:8000/app/sprites.js | grep -c "viewBox"` ≥ 1 and `/app/` shows all six JS sharing one `?v=` hash.
- [ ] **Step 3: Screenshot** onboarding/map/runner — confirm no emoji remain; sprites render in HUD, nodes, avatars, badges, mentor, boss.

---

## Self-Review (completed by plan author)

**Spec coverage (P4b of §4.2/§4.5):** `sprites.js` with `sprite()` + id maps → Task 1 ✓; emoji→sprite
at every site (stage icons, avatars, HUD, onboarding/picker, mentor, badges, boss crown, level-up
star, map marks) → Task 3 ✓; CSS sizing + include + cache-bust → Task 2 ✓.

**Placeholder scan:** No "TBD/etc"; every sprite, swap, and CSS rule is concrete.

**Type consistency:** `sprite(name)`/`AVATAR_SPRITES`/`STAGE_SPRITES`/`BADGE_SPRITES` defined in
Task 1 match all usages in Task 3; `avatarSprite`/`stageSprite`/`spr` guards keep `app.js`/`ui.js`
standalone-safe; `BADGES[code].ico` now holds sprite ids consumed via `spr` everywhere it renders.

## Out of scope (P4c)
- Winding level-path map layout + avatar travel marker + flags between nodes.
