# Design Spec — Phase 4 · P4: Arcade-Quest Visual Reskin

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phase 4 P1–P3 (live "رحلة الباحث")

## 1. Purpose

The current look reads as AI-generated/templated (violet→gold gradients everywhere, emoji
avatars/icons, an even stack of identical rounded cards, gradient-text headings, system font).
P4 replaces that with a **distinctive, intentional "Arcade Quest" aesthetic**: flat bold palette,
chunky pixel chrome, a CRT scanline, custom **SVG pixel-art sprites instead of emoji**, real
self-hosted display type, and a Mario-style level-path map.

**Hard constraint: frontend-only.** No backend/API/DB/content change. Every existing element
ID/class and all app logic are preserved (so the runner/report/board/badges/progress flow and all
tests keep working).

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Direction | **Arcade Quest** — flat bold palette, chunky borders + hard `4px 4px 0 #000` shadows, square/4px corners, **CRT scanline** overlay, no gradients/soft glows. |
| Typography | **Hybrid, self-hosted woff2** (no CDN): **Lalezar** (Arabic headings) + **Cairo** (Arabic body) + **Press Start 2P** (numbers/score/HUD/"LEVEL"). True pixel Arabic fonts don't exist; this keeps Arabic legible while signalling arcade. |
| Icons/avatars | **Replace ALL emoji with hand-authored inline SVG pixel sprites** (`shape-rendering:crispEdges`): avatar set, stage icons, badges, boss crown, pixel-owl mentor, map marks. |
| Palette | navy `#0b1e3f` base · panel `#13294d` · hot-pink `#ff5277` · gold `#ffd23f` · teal `#2ec4b6` · off-white `#eaf2ff` · ink `#06101f`. |
| Map | Winding **level-path**: stage tiles linked by a segmented path; avatar marker on the `next` tile; flag/checkmark on cleared tiles. |
| Scope | Reskin **all** screens (onboarding, map, runner, funfact, report, board, badges, progress). |

## 3. Architecture (frontend-only)

```
frontend/
  fonts/                 # CREATE: self-hosted woff2 (Lalezar, Cairo, PressStart2P) + LICENSE
  sprites.js             # CREATE: sprite(name) -> inline SVG string; AVATAR_SPRITES, STAGE_SPRITES, BADGE_SPRITES
  styles.css             # OVERHAUL: @font-face, flat palette, pixel chrome, scanline, level-path, sprite sizing
  index.html             # MODIFY: #scanline overlay; sprite/font wiring (script include)
  app.js                 # MODIFY: swap emoji literals (STAGE_EMOJI, AVATARS, mentor 🦉, BADGES ico, marks) for sprite() calls
```

- `sprites.js` exposes `window.sprite(name)` returning an SVG string, plus the sprite-id lists
  used where emoji are today. `app.js` calls `sprite(...)` (guarded: `typeof sprite === "function"`)
  so it still evaluates standalone in `runner.test.js`.
- All sprite/chrome/scanline work is presentation; **no element IDs/classes renamed**.
- Cache-busting (`main.py`) already stamps `app.js/ui.js/store.js/game.js/styles.css`; **add
  `sprites.js`** to that list. Fonts are static assets under `/app/fonts/` (not version-stamped;
  referenced by `@font-face` with their own filenames — fine, they don't change).

## 4. Components

### 4.1 Fonts (`frontend/fonts/`)
- Self-host woff2: `Lalezar-Regular.woff2` (Arabic display, OFL), `Cairo-SemiBold.woff2` +
  `Cairo-Bold.woff2` (Arabic body, OFL), `PressStart2P-Regular.woff2` (Latin/numerals, OFL).
- `@font-face` blocks in `styles.css`; `LICENSE`/attribution file in `fonts/`.
- Usage: `--font-head: "Lalezar"`, `--font-body: "Cairo"`, `--font-pixel: "Press Start 2P"`.
  Headings use head; body uses body; `.pixel` utility + score/level/HUD numerals use pixel.

### 4.2 Sprites (`frontend/sprites.js`)
- `sprite(name, opts) -> string` — returns an `<svg viewBox="0 0 16 16" shape-rendering="crispEdges" class="sprite">…</svg>` string built from a compact pixel grid (rects). Sizing via CSS (`.sprite{width:1.6em;height:1.6em}`), recolorable via `currentColor`/fills.
- Sets:
  - `AVATAR_SPRITES`: ids replacing the 8 emoji avatars (e.g. `scholar`, `scientist`, `owl`, `fox`, `cat`, `coder`, `grad-f`, `grad-m`).
  - `STAGE_SPRITES`: per slug — `foundations`(book), `paper-parts`(puzzle), `paper-types`(doc), `journals`(magnifier).
  - `BADGE_SPRITES`: `perfect_quiz`, `self_reliant`, `streak_master`, `first_finish`.
  - singles: `owl` (mentor), `crown` (boss), `flag`/`check` (map marks), `star` (level-up).

### 4.3 Chrome & scanline (`styles.css`)
- Replace gradient backgrounds with flat fills; cards/buttons get `border:3px solid var(--ink)` +
  `box-shadow:4px 4px 0 var(--ink)`; `border-radius:4px`. Active state translates `2px 2px` and
  drops shadow (physical press).
- `#scanline`: a fixed full-screen overlay, `pointer-events:none`,
  `background:repeating-linear-gradient(transparent 0 2px, #0006 2px 3px)` at low opacity + a faint
  vignette. Sits above content, below interactive overlays' own backdrops.
- Headings in Lalezar (no gradient-text); accents are flat hot-pink/gold/teal blocks.

### 4.4 Level-path map (`styles.css` + `app.js`)
- `#map-path` becomes a vertical winding path: nodes alternate left/right with a connecting
  segmented pseudo-element; `next` node shows the avatar marker; `done` shows a flag/check sprite;
  the node uses `STAGE_SPRITES[slug]`. Logic (`mapState`, `node.onclick`) unchanged.

### 4.5 `app.js` emoji → sprite swaps
- `STAGE_EMOJI[slug]` → `sprite(STAGE_SPRITES[slug])`.
- `AVATARS` (emoji array) → avatar **sprite ids**; onboarding/picker/HUD render `sprite(id)`;
  stored profile `avatar` becomes a sprite id string (back-compat: if a stored value isn't a known
  id, fall back to the `scholar` sprite).
- Mentor `🦉` (in `ob-mentor` + `mentorSay` card) → `sprite("owl")` (mentor card avatar slot).
- `BADGES[code].ico` (emoji) → `sprite(BADGE_SPRITES[code])` in report/badges/leaderboard.
- Boss banner crown, level-up star → sprites.

## 5. Out of scope (YAGNI / future)
- Backend/content/logic changes; sound; animated sprite sheets; per-pixel boss art.
- Changing question content, scoring, sampling, or any flow.

## 6. Testing
- **Vitest (jsdom):** `sprite(name)` returns non-empty SVG for every known id and a safe fallback
  for unknown ids; `AVATAR_SPRITES`/`STAGE_SPRITES`/`BADGE_SPRITES` cover the expected keys.
- **Existing guards stay green:** `runner.test.js` (sprite calls are `typeof`-guarded; `app.js`
  evaluates without `sprites.js`), `ui.test.js`/`store.test.js`/`game.test.js`, and the
  `drag.e2e.mjs` browser test (selectors/logic unchanged).
- **Visual verification:** puppeteer screenshots of onboarding/map/runner/report after deploy.

## 7. Decomposition (one spec → phased plan)
- **P4a — Theme system:** fonts (self-hosted) + flat palette + pixel chrome + scanline, applied to
  existing components. Biggest immediate visual shift; ships first.
- **P4b — Sprites:** `sprites.js` + replace every emoji with SVG pixel sprites.
- **P4c — Level-path map:** winding path layout + avatar marker + flags.

Each phase is independently shippable and gets its own implementation plan.
