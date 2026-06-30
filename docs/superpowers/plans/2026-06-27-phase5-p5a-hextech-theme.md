# Phase 5 · P5a — Hextech Theme Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the arcade pixel theme with the hextech core — self-hosted Aref Ruqaa/Cinzel fonts, the LoL navy/gold/cyan palette, gold-filigree notched frames, and a CSS/SVG painted atmosphere (fog, glow, runes, vignette) in place of the CRT scanline.

**Architecture:** Pure presentation. Self-host two woff2 fonts; rewrite the `:root` palette, base, and chrome rules in `styles.css`; swap `#scanline` for an `#atmos` layered-gradient overlay. No markup IDs/classes renamed; no JS logic change. Component ornamentation (map/HUD/sprite frames/embers) is P5b.

**Tech Stack:** Dependency-free HTML/CSS; self-hosted woff2; Vitest/drag-e2e unchanged.

## Global Constraints

- **Frontend-only.** No backend/API/DB/content/logic change. Preserve every element ID/class.
- **Fonts self-hosted** in `frontend/fonts/` (no CDN): **Aref Ruqaa** (Arabic headings, OFL), **Cinzel** (Latin caps/numerals, OFL). Keep **Cairo** (body). Retire **Press Start 2P** usage.
- **Palette (flat + glow):** `--bg:#010a13` · `--panel:#0a1428` · `--panel2:#0a323c` · `--ink:#010406` · `--gold:#c8aa6e` · `--gold-bright:#f0e6d2` · `--gold-dim:#785a28` · `--gold-line:#463714` · `--cyan:#0ac8b9` · `--cyan-2:#0397ab` · `--cyan-bright:#cdfafa` · `--fg:#f0e6d2` · `--muted:#a09b8c` · `--bad:#ff4655` · `--good:#0ac8b9`.
- **Chrome:** dark translucent fills; **notched corners** via `clip-path`; **double gold hairline** border; gold text; hover/active = gold **glow** (`box-shadow:0 0 12px #c8aa6e66`); NO pixel hard-shadows / translate-press.
- **Atmosphere replaces the scanline** (`#scanline` removed; `#atmos` added): layered radial gradients (teal top glow + gold ember glow), blurred fog, vignette. Keep keyframe names used by app/tests (`screen-in`, `pop-good`, `shake`, `confetti-fall`, `node-pulse`).
- **Arabic, RTL.** Headings use Aref Ruqaa; numerals/caps use Cinzel; body Cairo.
- **All existing tests stay green:** `./scripts/test.sh` (pytest 117 + vitest 33 + drag e2e). No new JS file in P5a, so no `main.py` change.
- Tests run from `frontend/`.

---

## File Structure

```
frontend/
  fonts/         # CREATE: ArefRuqaa-Bold.woff2, Cinzel-SemiBold.woff2 (+ OFL note)
  styles.css     # MODIFY: @font-face, palette, base, hextech chrome; retire pixel chrome
  index.html     # MODIFY: replace <div id="scanline"> with <div id="atmos">
```

---

### Task 1: Self-host Aref Ruqaa + Cinzel

**Files:**
- Create: `frontend/fonts/{ArefRuqaa-Bold.woff2, Cinzel-SemiBold.woff2}`; Modify `frontend/fonts/OFL.txt`
- Modify: `frontend/styles.css` (`@font-face` + font vars)

**Interfaces:** Produces CSS vars `--font-head` (Aref Ruqaa), `--font-caps` (Cinzel), `--font-body` (Cairo).

- [ ] **Step 1: Download the woff2** (Google Fonts → self-host)

Run:
```bash
cd /mnt/data/projects/Boundless/Gamified-sessions/frontend && python3 - <<'PY'
import urllib.request, re
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
def grab(css_url, subset, out):
    css = urllib.request.urlopen(urllib.request.Request(css_url, headers={"User-Agent": UA}), timeout=20).read().decode()
    blocks = re.split(r"/\*\s*([a-z0-9-]+)\s*\*/", css)
    url = None
    for i in range(1, len(blocks), 2):
        if blocks[i] == subset:
            m = re.search(r"url\((https://[^)]+\.woff2)\)", blocks[i+1])
            if m: url = m.group(1); break
    assert url, f"no {subset} woff2 in {css_url}"
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read()
    open(out, "wb").write(data); print("wrote", out, len(data), "bytes")
grab("https://fonts.googleapis.com/css2?family=Aref+Ruqaa:wght@700&display=swap", "arabic", "fonts/ArefRuqaa-Bold.woff2")
grab("https://fonts.googleapis.com/css2?family=Cinzel:wght@600&display=swap", "latin", "fonts/Cinzel-SemiBold.woff2")
PY
printf '\n- Aref Ruqaa (c) the Aref Ruqaa Project Authors\n- Cinzel (c) Natanael Gama\n' >> fonts/OFL.txt
ls -la fonts/*.woff2
```
Expected: both `.woff2` written (non-empty). If Google Fonts is unreachable, STOP and report.

- [ ] **Step 2: Add `@font-face` + replace font vars** at the top of `frontend/styles.css`. Replace
the three existing `@font-face` lines (Lalezar/Cairo/PressStart2P) with Cairo + the two new faces:

```css
@font-face { font-family:"Cairo"; src:url("fonts/Cairo-arabic.woff2") format("woff2"); font-weight:600; font-display:swap; }
@font-face { font-family:"ArefRuqaa"; src:url("fonts/ArefRuqaa-Bold.woff2") format("woff2"); font-weight:700; font-display:swap; }
@font-face { font-family:"Cinzel"; src:url("fonts/Cinzel-SemiBold.woff2") format("woff2"); font-weight:600; font-display:swap; }
```

(Cairo-arabic.woff2 already exists from P4a.)

- [ ] **Step 3: Run the suite (no regression from CSS)**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: vitest 33 pass; drag e2e passes.

- [ ] **Step 4: Commit**

```bash
git add frontend/fonts frontend/styles.css
git commit -m "feat(p5a): self-host hextech fonts (Aref Ruqaa, Cinzel)"
```

---

### Task 2: Hextech palette + base + headings

**Files:** Modify `frontend/styles.css` (`:root`, `body`/`#app`, headings)

**Interfaces:** Consumes font faces (Task 1). Produces the hextech palette + typographic base; no selectors renamed.

- [ ] **Step 1: Replace the `:root` block** (the P4 arcade palette) with the hextech palette + font vars:

```css
:root {
  --bg:#010a13; --panel:#0a1428; --panel2:#0a323c; --ink:#010406;
  --gold:#c8aa6e; --gold-bright:#f0e6d2; --gold-dim:#785a28; --gold-line:#463714;
  --cyan:#0ac8b9; --cyan-2:#0397ab; --cyan-bright:#cdfafa;
  --fg:#f0e6d2; --muted:#a09b8c; --bad:#ff4655; --good:#0ac8b9;
  /* legacy aliases so older rules keep resolving */
  --card:#0a1428; --card2:#0a323c; --accent:#c8aa6e; --accent2:#c8aa6e; --pink:#c8aa6e; --teal:#0ac8b9; --bg2:#010a13;
  --font-head:"ArefRuqaa", "Cairo", serif;
  --font-caps:"Cinzel", serif;
  --font-body:"Cairo", system-ui, "Segoe UI", Tahoma, sans-serif;
  --font-pixel:"Cinzel", serif; /* retire pixel: numerals now use Cinzel */
}
```

- [ ] **Step 2: Replace `body` / `#app`** with the deep hextech base:

```css
body { margin:0; color:var(--fg); font-family:var(--font-body); background:var(--bg); min-height:100vh; }
#app { max-width:560px; margin:0 auto; padding:16px; position:relative; z-index:1; }
```

- [ ] **Step 3: Replace headings** (the P4a `h1,h2,h3` + `h1` rules) with engraved gold:

```css
h1, h2, h3 { text-align:center; font-family:var(--font-head); font-weight:700; color:var(--gold-bright); letter-spacing:1px; }
h1 { font-size:2.3rem; color:var(--gold); text-shadow:0 0 14px #c8aa6e55, 0 2px 0 #000; }
h2 { font-size:1.5rem; }
```

- [ ] **Step 4: Run the suite**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css
git commit -m "feat(p5a): hextech palette + engraved gold headings"
```

---

### Task 3: Hextech chrome (frames, buttons, options)

**Files:** Modify `frontend/styles.css` (button/option/card chrome; append a `.hx-frame` utility)

**Interfaces:** Produces the hextech notched-gold-frame chrome on all existing button/card selectors.

- [ ] **Step 1: Replace the `button, .opt` chrome block** (the P4a pixel chrome) with hextech frames:

```css
button, .opt {
  display:block; width:100%; margin:8px 0; padding:14px; cursor:pointer; text-align:right;
  color:var(--gold-bright); font-family:var(--font-body); font-weight:600; font-size:1rem;
  background:linear-gradient(180deg, #0a1428ee, #06101dee);
  border:1px solid var(--gold-dim); outline:1px solid #0a1f33; outline-offset:-4px;
  clip-path:polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  transition:box-shadow .18s ease, color .18s ease, border-color .18s ease;
}
button:hover, .opt:hover { border-color:var(--gold); color:#fff; box-shadow:0 0 12px #c8aa6e55, inset 0 0 18px #0ac8b922; }
button:active, .opt:active { box-shadow:0 0 6px #c8aa6e66 inset; }
.opt.good, .opt.correct { border-color:var(--cyan); color:var(--cyan-bright); box-shadow:0 0 14px #0ac8b955; }
.opt.bad, .opt.wrong { border-color:var(--bad); color:#ffd7da; box-shadow:0 0 14px #ff465555; }
#btn-board, #btn-home, .quiz-card { color:var(--gold-bright); text-align:center; font-weight:700;
  background:linear-gradient(180deg,#123,#0a1428); border-color:var(--gold); }
```

- [ ] **Step 2: Replace the shared card rule** (the P4a `.report-item, ol#board-list li, …` block) with the hextech panel look (same selector list, keep IDs):

```css
.report-item, ol#board-list li, #funfact-text, .badge, .dash-stats .stat, .dash-history li,
.map-hud, .map-node, .mentor-card, .levelup-card {
  background:linear-gradient(180deg,#0a1428dd,#06101ddd);
  border:1px solid var(--gold-dim); border-radius:0;
  clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px);
  box-shadow:inset 0 0 0 1px #0a1f33, 0 0 0 0 transparent;
}
.summary-big { font-family:var(--font-caps); font-size:1.7rem; text-align:center; margin:12px 0;
  color:var(--gold); letter-spacing:2px; text-shadow:0 0 12px #c8aa6e66; }
.report-item { padding:12px; margin:8px 0; }
```

- [ ] **Step 3: Append the `.hx-frame` corner-ornament utility** to `frontend/styles.css`:

```css
/* ---- P5a hextech frame ornaments ---- */
.hx-frame { position:relative; }
.hx-frame::before, .hx-frame::after {
  content:""; position:absolute; width:14px; height:14px; pointer-events:none;
  border-color:var(--gold); border-style:solid; opacity:.85;
}
.hx-frame::before { top:-1px; inset-inline-start:-1px; border-width:2px 0 0 2px; }
.hx-frame::after { bottom:-1px; inset-inline-end:-1px; border-width:0 2px 2px 0; }
.level-bar { height:12px; border-radius:0; background:#04111c; border:1px solid var(--gold-dim); overflow:hidden; }
.level-bar > i { display:block; height:100%; background:linear-gradient(90deg,var(--cyan-2),var(--cyan-bright)); box-shadow:0 0 10px #0ac8b988; transition:width .6s cubic-bezier(.2,.8,.2,1); }
```

- [ ] **Step 4: Run the suite**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green (selectors unchanged).

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css
git commit -m "feat(p5a): hextech notched-gold-frame chrome + level bar"
```

---

### Task 4: Painted atmosphere (retire scanline)

**Files:** Modify `frontend/index.html` (`#scanline` → `#atmos`), `frontend/styles.css` (atmosphere + numerals + remove pixel scanline rule)

**Interfaces:** Produces the layered hextech atmosphere behind the app; numerals use Cinzel.

- [ ] **Step 1: Swap the overlay element in `frontend/index.html`** — replace
`<div id="scanline"></div>` (right after `<body>`) with:

```html
  <div id="atmos"></div>
```

- [ ] **Step 2: Replace the `#scanline` CSS rule** in `frontend/styles.css` with `#atmos` + numerals:

```css
/* ---- P5a hextech atmosphere ---- */
#atmos {
  position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(120% 80% at 50% -10%, #0a323c55 0%, transparent 55%),
    radial-gradient(90% 60% at 50% 110%, #785a2833 0%, transparent 55%),
    radial-gradient(60% 40% at 80% 20%, #0ac8b915 0%, transparent 60%),
    radial-gradient(140% 120% at 50% 50%, transparent 55%, #000a 100%),
    var(--bg);
}
.hud-rank, #progress, .summary-big, .levelup-title, .dash-stats .stat b { font-family:var(--font-caps); letter-spacing:1px; }
.hud-rank { font-size:.75rem; color:var(--gold); }
#progress { font-size:.9rem; color:var(--gold); }
```

(Delete the old `#scanline { … }` rule.)

- [ ] **Step 3: Verify the app sits above the atmosphere** — `#app` has `z-index:1` (Task 2) and
`#atmos` is `z-index:0`; interactive overlays (`.mentor-overlay` etc.) are `z-index:10000+`. No edit
needed unless a check fails.

- [ ] **Step 4: Run the suite**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/styles.css
git commit -m "feat(p5a): painted hextech atmosphere replaces CRT scanline"
```

---

### Task 5: Full-suite gate + deploy + screenshot

**Files:** none.

- [ ] **Step 1: Combined suite** — `./scripts/test.sh` → backend 117; frontend vitest 33; drag e2e.
- [ ] **Step 2: Selector regression check** —
  `cd frontend && for s in screen-runner q-options order-row chip opt quiz-card map-hud atmos hud-rank; do grep -q "$s" styles.css index.html app.js && echo "ok: $s" || echo "MISSING: $s"; done`
  Expected: `ok:` for each (and `MISSING: scanline` is fine — intentionally removed).
- [ ] **Step 3: Deploy (frontend-only; no reseed)** — `docker compose up -d --build`; verify
  `curl -s localhost:8000/health` → ok; `curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/app/fonts/ArefRuqaa-Bold.woff2` → 200; `curl -s localhost:8000/app/styles.css | grep -c "ArefRuqaa"` ≥ 1.
- [ ] **Step 4: Screenshot** onboarding/map/runner with the puppeteer helper and confirm the hextech
  look (deep navy, gold notched frames, Aref Ruqaa headings, cyan glows, atmosphere).

---

## Self-Review (completed by plan author)

**Spec coverage (P5a slice of §7):** self-hosted Aref Ruqaa/Cinzel (§4.1) → Task 1; hextech palette
(§3) + engraved headings → Task 2; notched gold-frame chrome + `.hx-frame` + level bar (§4.2) →
Task 3; painted atmosphere replacing scanline (§4.3) → Task 4; numerals→Cinzel, pixel retired →
Tasks 2/4. Component ornamentation (map/HUD/sprite frames/embers) is P5b, out of this plan.

**Placeholder scan:** No "TBD/handle later" — the font script and every CSS block are concrete.

**Type consistency:** Font vars `--font-head/caps/body` defined in Task 1 `@font-face` + Task 2
`:root`, consumed in Tasks 2–4. Legacy palette aliases (`--card/--accent/--good/--bad/--teal/--pink`)
kept in `:root` so P1–P4 rules referencing them still resolve to hextech colors. Keyframe names
unchanged. `#atmos` (Task 4 index.html) matches its CSS rule.

## Out of scope (P5b)
- Map ascension-path restyle, HUD panel, overlays-as-hextech-cards, sprite gold-hex frames, gold
  ember particles (`embers()`).
