# رحلة الباحث × Arcane — Mega Design DNA & Reskin Spec

> **Status:** approved direction (2026-06-30). Supersedes the Phase-5 "hextech" reskin, which
> implemented only the *Piltover half* of Arcane and read as clean hextech UI rather than the show.
> **Visual target:** Figma file `5vZ86weOps1hxDtG3fqQcg`
> (`https://www.figma.com/design/5vZ86weOps1hxDtG3fqQcg`) — the "Ascension Map" screen.

## 1. Why the current build misses

Netflix/Riot's **Arcane** (Fortiche) has four signatures the current theme lacks:

1. **Two warring worlds, two palettes that collide** — luminous **Piltover** (gold/brass, ivory,
   art-deco, hextech cyan) vs the toxic **Zaun** undercity (shimmer-magenta, chemtech acid-green,
   smog, neon graffiti). The old theme was navy+gold+cyan only — half the identity.
2. **Painterly texture** — hand-painted brushstroke surfaces, volumetric god-rays, dust/embers,
   heavy bloom. Flat CSS gradients read "clean UI," not "oil-painted frame."
3. **Fractured / engraved display type** — the ARCANE logotype is tall, condensed, cracked.
4. **Character DNA** — the cast carries the brand. Generic sprites don't.

## 2. The core metaphor

**The research journey *is* the climb out of Zaun.** The player begins as an undercity tinkerer
wrestling raw ideas (shimmer-magenta + acid-green, smog, graffiti). Each mastered concept lifts them
up the bridge. True mastery arrives in luminous **Piltover** (gold, cyan hextech, art-deco order).
Bosses are **"shimmer surges"** that drag the player back toward the undercity.

This maps cleanly onto existing mechanics: **level/XP/rank** → altitude on the climb; **map nodes** →
waypoints on the ascent; **bosses** → shimmer surges; **mastery** → Piltover light.

## 3. Palette — two poles + a world-lerp

All values are authored as CSS custom properties on `:root`. The two poles:

| Token | Zaun (early / danger) | Piltover (mastery / goal) |
|---|---|---|
| `--z-shimmer` / `--p-gold` | `#ff2e97` | `#c8aa6e` |
| `--z-acid` / `--p-cyan` | `#2fe6a0` | `#0ac8b9` |
| `--z-violet` / `--p-bright` | `#8a3bff` | `#e2c687` |
| surface base | `#14081e` (smog) | `#0a1428` (navy) |
| surface raised | `#1f0f2e` | `#0e1b33` |
| ink / ivory | `#e8d8ff` | `#f0e6d2` |

**Shared / semantic:**
`--gold:#c8aa6e`, `--gold-bright:#e2c687`, `--gold-dim:#785a28`, `--cyan:#0ac8b9`,
`--shimmer:#ff2e97`, `--acid:#2fe6a0`, `--bad:#ff4655`, `--good:#0ac8b9`.

**World-lerp engine.** A single scalar `--world` (0 = deep Zaun … 1 = high Piltover) drives the
ambient mood. The frontend sets `document.documentElement.style.setProperty('--world', t)` where
`t = clamp(level-progress)`. Background tints, ember color, and accent glow interpolate between poles
via `color-mix(in srgb, var(--z-…) calc((1 - var(--world)) * 100%), var(--p-…))`. Default per screen:
home/map low-mid, runner mid, report tinted by score, board/badges Piltover.

**Legacy aliases stay.** Keep `--card`, `--accent`, `--pink`, `--teal` mapped onto the new palette so
P1–P4 rules resolve unchanged (the established reskin technique).

## 4. Typography

| Role | Font (self-hosted woff2) | Treatment |
|---|---|---|
| Arabic display / titles | **Aref Ruqaa** Bold | gold `--gold-bright`, dual drop-shadow (cyan glow + dark offset) for an engraved edge |
| Latin caps / numerals / crests | **Cinzel** Bold | letter-spaced small-caps, `THE ARCANE ASCENT`, `Lv 3`, `3/10` |
| Arabic body / questions | **Cairo** (SemiBold/Bold) | high-legibility, `line-height:1.7`, no letter-spacing |

Fonts already self-hosted in `frontend/fonts/`. "Fractured" is approximated with the engraved
shadow + a faint 1px gold text-stroke on titles (no per-glyph fracture — out of scope).

## 5. Texture & atmosphere system (the Fortiche layer)

A reusable, GPU-cheap stack — **no raster assets required**, all CSS/SVG:

1. **`#atmos`** (fixed, behind `#app`): the two-world vertical gradient + layered radial glows
   (Piltover gold halo + cyan spark up top; Zaun shimmer + acid down low), tinted by `--world`.
2. **God-rays:** 3–4 thin, rotated, low-opacity gold gradient bars near the top, `mix-blend:screen`.
3. **Grain:** a tiling SVG `feTurbulence` overlay at ~4–6% opacity for painterly tooth.
4. **Bloom:** glows use `box-shadow`/`drop-shadow` with the accent color, never hard edges.
5. **Embers:** `embers()` already exists; extend to **dual embers** — magenta sparks rise from the
   Zaun floor, gold motes drift up top; color picked from `--world`.

All decorative layers are `pointer-events:none`, honor `prefers-reduced-motion` (freeze drift), and
sit at low z so content stays crisp.

## 6. The cast — Arcane-inspired archetypes (CSS/SVG, no IP)

Original silhouettes drawn in `sprites.js` (inline SVG, existing `sprite(name)` system). Evocative,
**not** copyrighted likenesses; leave slots for user-supplied art later.

| Archetype | Role in app | Visual cues |
|---|---|---|
| **The Tinkerer** | mentor / guide | goggles, brass cogwork, warm gold — the inventor |
| **The Brawler** | grit / retry energy | oversized gauntlets, pink hair-flash, scrappy |
| **The Sniper** | precision / Piltover | top-hat, monocle/scope, blue-gold |
| **The Gremlin** | boss / shimmer surge | wild silhouette, magenta sparks, chaos |
| **The Alchemist** | Zaun ambience | hood, vials, acid-green glow |

Avatars become a **"choose your champion"** set (replaces scholar/scientist/coder/owl/fox/cat).
Bosses pick from Gremlin/Alchemist with a shimmer-surge banner.

## 7. Per-screen treatment

- **Map (signature):** §3 two-world `#atmos`, dashed climbing trail, tiered glow-nodes (magenta done
  → cyan "you are here" → red boss), Cinzel numerals, `PILTOVER`/`ZAUN` region labels, HUD panel
  (champion token + name + rank + `Lv` + XP bar), dual embers. Matches the Figma target.
- **Runner / question:** smog-navy field; notched **gold-frame** question card; **shimmer "boss
  surge"** banner (magenta→red) when a boss is active; gold-rim option buttons that flash cyan on
  correct / shimmer on wrong; Cinzel `3/10`; passage screenshots framed as "evidence dossiers."
- **Funfact:** a hextech-crystal interstitial card, cyan glow, calligraphic heading.
- **Report:** `--world` tinted by score (low → Zaun, high → Piltover ascension); champion token;
  gold filigree dividers; rank-up moment uses the level-up overlay.
- **Board / badges:** Piltover-gold gold-token frames; badges locked = grayscale undercity.
- **Onboarding:** "choose your champion" + the mentor (Tinkerer) intro line.

## 8. Motion

- Ember drift (existing keyframes), `crystal-pulse` on the next/active node, god-ray slow shimmer,
  button glow transitions, level-up burst. All ≤ existing budget; all frozen under reduced-motion.

## 9. Constraints

- **Frontend-only.** No backend / API / DB / content / scoring change. Every element ID/class
  preserved. All module calls from `app.js` stay `typeof`-guarded (standalone eval for `runner.test.js`).
- **Dependency-free.** No new libraries. Self-hosted fonts only.
- **RTL Arabic** throughout. **Telegram Mini App** safe-areas respected.
- **Cache-busting** already covers `styles.css`/`*.js` via `main.py` bundle hash — never hand-edit `?v=`.
- All existing tests stay green: `./scripts/test.sh` (117 py + 35 frontend + drag e2e), plus new
  unit tests for the world-lerp helper and dual embers.

## 10. Out of scope (future)

- Per-glyph fractured lettering; raster/AI painterly backgrounds and hero portraits (user may supply
  art into `content/assets/` later — the atmosphere stack is built to layer under them).
- Any literal Arcane character likeness (IP).
- Audio.

## 11. Decomposition (for the implementation plan)

1. **Foundation** — palette tokens + `--world` lerp engine + legacy aliases (+ unit test).
2. **Atmosphere** — `#atmos` two-world gradient, god-rays, grain, dual embers (+ ember test).
3. **Cast** — champion/boss/mentor SVG archetypes in `sprites.js`, avatar picker wiring.
4. **Screens** — map, runner/boss, funfact, report, board/badges, onboarding restyle.
5. **Gate** — full suite + deploy + screenshot parity vs the Figma target.
