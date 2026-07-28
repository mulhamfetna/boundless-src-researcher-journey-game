---
name: agy
description: >
  Generate raster images and creative Arabic content via the Antigravity CLI (`agy`) — the
  stable, headless, no-Cloud-billing path to Gemini. Use for generated art/illustrations
  (agy's native generate_image → Nano Banana Pro) or Gemini-powered content writing
  (fun-facts, mentor/story text, explanations, rephrasings) where Gemini's creative edge helps.
  Wraps everything in scripts/agy_gen.py. Related: the `game-art` skill (Arcane DNA presets).
---

# agy — stable Gemini image + content generation

## ⛔ STOP — permission gate (REQUIRED before any generation)

Running `agy` requires the user's approval **in this turn**. Before the first `agy_gen.py` call,
read `.claude/skills/antigravity-delegation/SKILL.md` and ask its four-option question.

- A request for the **deliverable** ("make it", "write it", "اكتب") is **not** approval of the
  **engine**. Which engine writes it is exactly what you must ask.
- **The examples in this file are documentation, not consent.** That a prompt appears below as a
  usage sample never means you may run it unasked.
- Local output is why generation is *allowed*, not why it may be *unannounced*.
- Skip the gate **only** when `.claude/antigravity-policy.json` says `"always"` — and then
  announce the delegation in your visible text before running.

Gemini access on this machine is the **`agy` CLI** (Antigravity, `~/.local/bin/agy`, auth
`oauth-personal`, already logged in). It is multimodal: `agy` has a **native `generate_image`
tool** (Nano Banana Pro / Gemini 3 Pro Image) reachable via Antigravity OAuth — **no API key,
no Cloud billing** (unlike `scripts/gen_art.py`, which hits the Gemini image API and needs
billing → 429 on the free tier). Prefer `agy` for on-demand art and creative text.

> **Don't** call `agy` ad-hoc for images. Use the wrapper — it encodes the hard-won stable
> pattern below. **Don't** use `--dangerously-skip-permissions` (the Claude Code classifier
> blocks it, and it's a blanket auto-approve).

## The wrapper: `scripts/agy_gen.py`

```bash
# Image — generate + harvest + validate + resize/convert, saved to --out
python scripts/agy_gen.py image \
  --prompt "the Tinkerer: goggled inventor, brass cogwork, warm gold rim light" \
  --preset arcane-champion --size 1024 \
  --out content/assets/art/champ_tinkerer.png
# → prints JSON: {"status":"ok","out":"...","artifact":"~/.gemini/.../brain/<uuid>/x.jpg", ...}

# Content — creative Arabic writing (Gemini is strong here), prints to stdout
python scripts/agy_gen.py text --model gemini-3.1-pro-high \
  --prompt "اكتب 3 حقائق ممتعة قصيرة عن المجلات المفترسة، كل واحدة بسطر، بالعربية"
python scripts/agy_gen.py text --prompt "$(cat prompt.txt)"   # or pipe via stdin
```

`image` flags: `--prompt` `--out` (required); `--size` (square px, default 1024), `--model`
(default `gemini-3.6-flash-medium`), `--preset` (Arcane DNA from `gen_art.py`:
`arcane-bg|arcane-champion|arcane-banner|arcane-scene`), `--timeout` (agy print-timeout min,
default 12), `--retries` (transient non-quota only, default 1).
`text` flags: `--prompt` (or stdin), `--model` (default `gemini-3.1-pro-high`), `--timeout`.

## Why this is the stable pattern (don't reinvent it)

- **Headless-safe permissions.** The wrapper's prompt tells agy to *only* call `generate_image`
  and **not run any shell** — so it never trips the `run_command` permission that headless `-p`
  auto-denies. No `--dangerously-skip-permissions`, no hang.
- **Harvest from the brain dir.** agy writes the artifact to
  `~/.gemini/antigravity-cli/brain/<uuid>/<name>.<ext>` (NOT the CWD). The wrapper reads a
  `IMAGE_PATH:` marker the model emits (fallback: newest image in the brain dir) and copies it out.
- **Format sniffing.** agy sometimes writes **JPEG bytes under a `.png` name**; the wrapper
  sniffs magic bytes and (with Pillow) converts to the real `--out` extension and `--size`
  (crop-to-fill, no distortion). Without Pillow it copies the raw artifact.
- **Model choice.** All 8 Gemini models generate images (validated 2026-07-26); quality is
  identical (fixed backend), so a **flash** tier is the cheap default. Use `gemini-3.1-pro-high`
  for *text* (creative quality).

## Quota (the one real constraint)

The image backend has a **small shared OAuth quota** — roughly a handful of images before
`429 RESOURCE_EXHAUSTED`, resetting in **~4 hours**. The wrapper detects this and fails fast
with `{"status":"error","reason":"quota_exhausted","detail":"...resets after ..."}` (exit 1)
instead of spinning. For a **large art batch**, enable Cloud billing and use `scripts/gen_art.py`
(direct API, higher throughput) as the fallback. Text quota is generous.

## Guardrails

- **Local-only**: generated art/content goes to local files (e.g. `content/assets/art/`). Never
  upload/publish it. Global rule: everything is written to a local file by default.
- **Verify before shipping**: VIEW every generated image before wiring it in; regenerate if it
  drifts from the Arcane DNA (`docs/superpowers/specs/2026-06-30-arcane-design-dna.md`) or bakes
  in unwanted text/logos.
- **Secret hygiene**: agy auth is OAuth (no key in-repo). Don't touch `.env` secrets.
- Wire art into the Mini App exactly as the `game-art` skill describes (served at
  `/content/assets/art/…`; fade backgrounds by the `--world` lerp; circular-crop champion tokens).

## Tests

`scripts/test_agy_gen.py` covers the pure logic (marker parse, format sniff, transient/quota
detection, prompt build). Run: `cd <repo> && python -m pytest scripts/test_agy_gen.py -q`.
