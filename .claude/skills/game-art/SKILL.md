---
name: game-art
description: >
  Generate on-brand Arcane game art (painterly backgrounds, champion portraits, station
  banners) for the رحلة الباحث quiz via the Gemini API, then wire the assets into the Mini
  App. Use when the user wants generated/raster art, illustrations, backgrounds, hero/champion
  portraits, or scene banners for this project — anything beyond CSS/SVG that Claude can't paint.
---

# game-art — Arcane art pipeline (Gemini)

Claude paints the UI in CSS/SVG but can't render raster/painterly art. This skill uses the
project's Gemini key to generate that art and layer it under the existing hextech UI.

> **Prefer `scripts/agy_gen.py` (the `agy` skill) for generation** — it uses the Antigravity
> CLI's `generate_image` (Nano Banana Pro) via OAuth with **no Cloud billing**, and shares these
> exact Arcane presets: `python scripts/agy_gen.py image --preset arcane-champion --size 1024
> --prompt "…" --out content/assets/art/x.png`. `gen_art.py` below (direct Gemini image API) is
> the **fallback for large batches** once billing is enabled — agy's OAuth image quota is small
> (~a handful/≈4h). The wiring/DNA guidance in this skill still applies to both.

## Prerequisite (one-time) — enable billing

Image models (`gemini-*-image`, `imagen-*`) have **0 quota on the Gemini free tier** → every
image call returns **HTTP 429** until **billing is enabled** on the Google Cloud project
(`GEMINI_PROJECT` in `.env`, currently `projects/1051085430066`). Text models work on free tier.
Enable billing at <https://console.cloud.google.com/billing> for that project, then art gen works
with no code change. The key lives in the gitignored `.env` as `GEMINI_API_KEY` (never commit it).

## The generator

`scripts/gen_art.py` (stdlib only) reads `GEMINI_API_KEY` from env or `.env` and writes a PNG.

```bash
# Painterly two-world background (layers under #atmos):
python scripts/gen_art.py --preset arcane-bg --aspect 9:16 \
  --prompt "vertical scene: neon Zaun undercity rising to golden Piltover spires" \
  --out content/assets/art/map_bg.png

# Champion portrait (crop to a circular token):
python scripts/gen_art.py --preset arcane-champion --aspect 1:1 \
  --prompt "the Tinkerer — goggled inventor, brass cogwork, warm gold rim light" \
  --out content/assets/art/champ_tinkerer.png

# Restyle an existing image (Gemini-image models support a --ref input):
python scripts/gen_art.py --prompt "repaint in Arcane style, magenta shimmer" \
  --ref input.png --out content/assets/art/out.png
```

Flags: `--preset {arcane-bg,arcane-champion,arcane-banner,arcane-scene,none}` (prepends the
Arcane style DNA), `--model` (default `gemini-2.5-flash-image`; also `gemini-3-pro-image` for
higher quality, `imagen-4.0-generate-001` if enabled), `--aspect`, `--ref`.

## Visual DNA (keep every asset on-brand)

Source of truth: `docs/superpowers/specs/2026-06-30-arcane-design-dna.md`. In one line:
**Fortiche painterly** (oil brush-stroke, god-rays, bloom, deep contrast) in the **two-world
palette** — Piltover gold `#c8aa6e` + hextech cyan `#0ac8b9` + art-deco, versus Zaun
shimmer-magenta `#ff2e97` + acid-green `#2fe6a0` + smog/grime. Never bake in text/logos/UI.

## Wiring assets into the game (frontend, `frontend/`)

Assets are served at `/content/assets/art/<file>` (the `/content` static mount). Options:

- **Map/screen background** — add a fixed `<div id="art-bg">` *below* `#atmos` (z-index 0, under
  `#app`'s z-index 1); set `background-image:url("/content/assets/art/map_bg.png")`. Fade it by the
  world-lerp with `opacity: var(--world)` (Piltover art) or `calc(1 - var(--world))` (Zaun art) to
  match the reactive atmosphere. Keep it dark/low-contrast so panels stay readable.
- **Champion portraits** — crop square art to a circle (PIL: paste onto a circular mask) sized to
  the token frames; drop into the avatar picker / HUD by swapping the `sprite()` token for an
  `<img>` (or add an `AVATAR_ART` map keyed by champion id, used when art exists, else the SVG).
- **Station banners** — show a wide banner atop a stage's runner/intro screen.

Post-process with PIL (already available): resize to target, circular-crop champions, and keep
files reasonably small (these are Telegram Mini App assets). Deploy is frontend/content only:
`docker compose up -d --build web` (+ reseed only if you changed `content/questions`).

## Guardrails

- **Local-only**: generated art is written to local files under `content/assets/art/`. Do not
  upload/publish it anywhere.
- **Secret hygiene**: the key stays in `.env` (gitignored). Never print it or commit it.
- **Verify before shipping**: view every generated asset before wiring it in; regenerate if it
  drifts from the Arcane DNA or bakes in unwanted text.
