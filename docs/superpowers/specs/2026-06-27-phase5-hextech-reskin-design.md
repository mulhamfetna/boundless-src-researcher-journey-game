# Design Spec — Phase 5: Hextech / Arcane ("League of Legends") Reskin

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com (Mulham Fetna)
**Builds on / replaces:** Phase 4 P4 "arcade pixel" theme

## 1. Purpose

Restyle the live Mini App ("رحلة الباحث") into a **League of Legends / Arcane "hextech"** aesthetic:
deep navy-black, ornate gold filigree frames, engraved caps, glowing cyan + gold, painted-feeling
atmosphere. This **replaces** the Phase-4 arcade pixel theme (Press Start 2P, flat pixel chrome, CRT
scanline). Frontend-only; all gameplay, IDs, classes, and tests are preserved.

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Direction | LoL **hextech** UI + **CSS/SVG-painted atmosphere** (no raster/AI art — I have no image generator). |
| Replaces | The arcade pixel theme entirely (retire Press Start 2P, pixel chrome, scanline). |
| Arabic display font | **Aref Ruqaa** (OFL, calligraphic Arabic) — Cinzel is Latin-only and can't render Arabic. |
| Latin caps/numerals | **Cinzel** (OFL, engraved Roman caps — the LoL signature) for LEVEL/rank/numbers. |
| Body font | Keep **Cairo** (Arabic, already self-hosted). |
| Art | Hand-crafted CSS/SVG atmosphere (fog, glow, runes, embers, vignette); no character paintings. |

## 3. Palette (hextech)

```
--bg #010a13   --panel #0a1428   --panel2 #0a323c   --ink #010406
--gold #c8aa6e --gold-bright #f0e6d2 --gold-dim #785a28 --gold-line #463714
--cyan #0ac8b9 --cyan-2 #0397ab --cyan-bright #cdfafa
--fg #f0e6d2 --muted #a09b8c --bad #ff4655 --good #0ac8b9
```
Flat fills + glows; no gradients-as-buttons, no pixel hard-shadows.

## 4. Components

### 4.1 Fonts (`frontend/fonts/`, self-hosted woff2)
- Add `ArefRuqaa-Bold.woff2` (Arabic display) + `Cinzel-SemiBold.woff2` (Latin caps). Keep `Cairo`.
- Drop `PressStart2P` usage (file may remain unreferenced). Vars: `--font-head:"Aref Ruqaa"`,
  `--font-body:"Cairo"`, `--font-caps:"Cinzel"`.

### 4.2 Hextech chrome (`styles.css`)
- Panels/cards/buttons: dark translucent fill, **notched corners** (`clip-path` octagon/cut), a
  **double gold hairline** (outer `--gold` + inner `--gold-dim`), gold text. Hover/active → gold
  **glow** (`box-shadow: 0 0 12px #c8aa6e66`) + subtle fill lift; no translate-pixel press.
- A reusable `.hx-frame` utility + **SVG filigree corner** ornaments (small absolutely-positioned
  SVGs at the panel corners) applied to the major panels (map HUD, cards, overlays).

### 4.3 Painted atmosphere (`index.html` + `styles.css`)
- Replace `#scanline` with `#atmos`: a fixed, pointer-events-none stack of layered radial gradients
  (top teal hextech glow, lower gold ember glow), large blurred "fog" radials, and a vignette.
- Faint **hextech-rune** SVG motif (hexagons/lines) as a low-opacity background flourish.
- Slow **gold ember** particles: reuse `ui.js` particle approach but a new `embers()` (small gold
  motes drifting upward, looping) mounted ambiently on the map/home.

### 4.4 Components reskinned
- **Map** (`#map-path`): a hextech "ascension path" — gold rune-nodes on a glowing vertical line,
  `next` node = a pulsing **hextech crystal** marker; done = a gold seal. Keep the winding layout +
  logic from P4c; restyle only.
- **HUD**: a hextech panel; the level bar becomes a **cyan glow fill** inside a gold frame.
- **Mentor / level-up / boss / report / board / badges / progress / onboarding / report-issue**:
  hextech cards (gold frame + cyan glow), Aref Ruqaa headings, Cinzel numerals.
- **Sprites**: each sprite wrapped in a **gold hex-token frame** (CSS hexagon clip + gold ring +
  glow) so the existing pixel sprites read as "hextech relics" in the new world.

## 5. Out of scope (YAGNI / future)
- Raster/AI character art & painted backgrounds (no image tool); user may supply later and we wire in.
- Backend/content/logic changes; new screens; changing the sprite drawings (only their frames).
- Sound/music.

## 6. Testing
- **Existing tests stay green** (selectors/logic unchanged): runner/ui/store/game/sprites/report/
  passage Vitest suites + the `drag.e2e.mjs` browser test + backend pytest.
- Any new pure helper (`embers()`) gets a Vitest unit test (creates/cleans particles) mirroring
  `confetti`.
- **Visual verification:** puppeteer screenshots of onboarding/map/runner/report after each phase.
- No new automated "looks-right" assertion beyond selectors; visual is manual + screenshots.

## 7. Decomposition (one spec → phased plans)
- **P5a — Theme core:** fonts (Aref Ruqaa, Cinzel) + hextech palette + gold-filigree frames/buttons
  + painted atmosphere (`#atmos`, fog, vignette, runes) + retire scanline/pixel-font. Biggest shift;
  ships first.
- **P5b — Component ornamentation:** map ascension-path restyle, HUD/level-bar, overlays as hextech
  cards, sprite gold-hex frames, gold ember particles.

Each phase is independently shippable, frontend-only, and gets its own implementation plan.

## 8. Deployment

Frontend-only → rebuild → up (no reseed/migrate). Cache-busting auto-stamps `app.js/ui.js/store.js/
game.js/sprites.js/styles.css`; new fonts are static `/app/fonts/*` (self-hosted, no CDN).
