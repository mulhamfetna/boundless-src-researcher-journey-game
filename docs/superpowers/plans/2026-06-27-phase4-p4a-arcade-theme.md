# Phase 4 · P4a — Arcade Theme System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the gradient/system-font theme with the Arcade-Quest look — self-hosted display fonts, a flat bold palette, chunky pixel chrome (hard shadows, square corners, press states), and a CRT scanline.

**Architecture:** Pure presentation. Self-host woff2 fonts under `frontend/fonts/`; rewrite the palette and component chrome in `styles.css`; add a `#scanline` overlay in `index.html`. No markup IDs/classes renamed; no JS logic change. Sprites (P4b) and the level-path map (P4c) come next.

**Tech Stack:** Dependency-free HTML/CSS; self-hosted woff2; Vitest/drag-e2e unchanged.

## Global Constraints

- **Frontend-only.** No backend/API/DB/content/logic change. Preserve every element ID/class.
- **Fonts self-hosted** in `frontend/fonts/` (no CDN at runtime): Lalezar (Arabic headings), Cairo (Arabic body), Press Start 2P (numerals/HUD). OFL — include a `fonts/OFL.txt` note.
- **Palette (flat, no gradients):** `--bg:#0b1e3f` · `--panel:#13294d` · `--ink:#06101f` · `--pink:#ff5277` · `--gold:#ffd23f` · `--teal:#2ec4b6` · `--fg:#eaf2ff` · `--muted:#9fb3d6`.
- **Chrome:** `border:3px solid var(--ink)`, `box-shadow:4px 4px 0 var(--ink)`, `border-radius:4px`, press = translate `2px 2px` + drop shadow. No soft glows / gradient-text.
- **Arabic, RTL.** Keep existing keyframe names used by app/tests (`screen-in`, `pop-good`, `shake`, `confetti-fall`, `node-pulse`).
- **All existing tests stay green:** `./scripts/test.sh` (pytest 106 + vitest 28 + drag e2e). No new JS file in P4a, so no `main.py` change.
- Tests run from `frontend/`.

---

## File Structure

```
frontend/
  fonts/                 # CREATE: Lalezar-arabic.woff2, Cairo-arabic.woff2, PressStart2P-latin.woff2, OFL.txt
  styles.css             # MODIFY: @font-face, font vars, flat palette, pixel chrome, scanline, pixel numerals
  index.html             # MODIFY: add <div id="scanline"></div>
```

---

### Task 1: Self-host the fonts

**Files:**
- Create: `frontend/fonts/{Lalezar-arabic.woff2, Cairo-arabic.woff2, PressStart2P-latin.woff2, OFL.txt}`
- Modify: `frontend/styles.css` (add `@font-face` + font vars at the top)

**Interfaces:**
- Produces: CSS vars `--font-head`, `--font-body`, `--font-pixel` available to all rules.

- [ ] **Step 1: Download the woff2 subsets** (Google Fonts → self-host)

Run:
```bash
cd /mnt/data/projects/Boundless/Gamified-sessions/frontend && mkdir -p fonts && python3 - <<'PY'
import urllib.request, re
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
def grab(css_url, subset, out):
    req = urllib.request.Request(css_url, headers={"User-Agent": UA})
    css = urllib.request.urlopen(req, timeout=20).read().decode()
    # find the @font-face block for the wanted subset comment, take its woff2 url
    blocks = re.split(r"/\*\s*([a-z0-9-]+)\s*\*/", css)
    url = None
    for i in range(1, len(blocks), 2):
        if blocks[i] == subset:
            m = re.search(r"url\((https://[^)]+\.woff2)\)", blocks[i+1])
            if m: url = m.group(1); break
    assert url, f"no {subset} woff2 in {css_url}"
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read()
    open(out, "wb").write(data)
    print("wrote", out, len(data), "bytes")

grab("https://fonts.googleapis.com/css2?family=Lalezar&display=swap", "arabic", "fonts/Lalezar-arabic.woff2")
grab("https://fonts.googleapis.com/css2?family=Cairo:wght@600&display=swap", "arabic", "fonts/Cairo-arabic.woff2")
grab("https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap", "latin", "fonts/PressStart2P-latin.woff2")
PY
printf 'Fonts are licensed under the SIL Open Font License 1.1:\n- Lalezar (c) Borna Izadpanah, Bonahonar\n- Cairo (c) the Cairo Project Authors\n- Press Start 2P (c) CodeMan38\nSee https://openfontlicense.org\n' > fonts/OFL.txt
ls -la fonts/
```
Expected: three non-empty `.woff2` files + `OFL.txt`.

(If Google Fonts is unreachable in your environment, STOP and report — do not ship without the
woff2 files; the `@font-face` would 404 and fall back to system fonts.)

- [ ] **Step 2: Add `@font-face` + font vars** at the very top of `frontend/styles.css` (before `:root`)

```css
@font-face { font-family:"Lalezar"; src:url("fonts/Lalezar-arabic.woff2") format("woff2"); font-display:swap; }
@font-face { font-family:"Cairo"; src:url("fonts/Cairo-arabic.woff2") format("woff2"); font-weight:600; font-display:swap; }
@font-face { font-family:"PressStart2P"; src:url("fonts/PressStart2P-latin.woff2") format("woff2"); font-display:swap; }
```

- [ ] **Step 3: Run the suite (no regression from adding CSS)**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: vitest 28 pass; drag e2e passes (no selector/logic change).

- [ ] **Step 4: Commit**

```bash
git add frontend/fonts frontend/styles.css
git commit -m "feat(p4a): self-host arcade display fonts (Lalezar/Cairo/Press Start 2P)"
```

---

### Task 2: Flat palette + pixel chrome

**Files:**
- Modify: `frontend/styles.css` (replace `:root`, base, button/card/option/headings rules)

**Interfaces:**
- Consumes: font vars (Task 1). Produces: the flat arcade theme; no selectors renamed.

- [ ] **Step 1: Replace the `:root` block** (the current P1 palette) with the arcade palette + font vars:

```css
:root {
  --bg:#0b1e3f; --panel:#13294d; --panel2:#1b3566; --ink:#06101f;
  --pink:#ff5277; --gold:#ffd23f; --teal:#2ec4b6; --fg:#eaf2ff; --muted:#9fb3d6;
  /* legacy aliases so older rules keep working */
  --card:#13294d; --card2:#1b3566; --accent:#ff5277; --accent2:#ff5277; --good:#2ec4b6; --bad:#ff5277; --bg2:#0b1e3f;
  --font-head:"Lalezar", system-ui, sans-serif;
  --font-body:"Cairo", system-ui, "Segoe UI", Tahoma, sans-serif;
  --font-pixel:"PressStart2P", monospace;
}
```

- [ ] **Step 2: Replace the `body` / `#app` rules** with flat fills:

```css
body {
  margin:0; color:var(--fg); font-family:var(--font-body);
  background:var(--bg); min-height:100vh;
}
#app { max-width:560px; margin:0 auto; padding:16px; }
```

- [ ] **Step 3: Replace headings + button/option/card chrome** (the P1 gradient rules):

```css
h1, h2, h3 { text-align:center; font-family:var(--font-head); font-weight:400; letter-spacing:.5px; color:var(--fg); }
h1 { color:var(--gold); text-shadow:3px 3px 0 var(--ink); font-size:2.1rem; }

button, .opt {
  display:block; width:100%; margin:8px 0; padding:14px; border:3px solid var(--ink); border-radius:4px;
  background:var(--panel); color:var(--fg); font-size:1rem; font-family:var(--font-body); font-weight:600;
  cursor:pointer; text-align:right; box-shadow:4px 4px 0 var(--ink); transition:transform .06s steps(2), box-shadow .06s steps(2);
}
button:active, .opt:active { transform:translate(2px,2px); box-shadow:2px 2px 0 var(--ink); }
.opt.good, .opt.correct { background:var(--teal); color:var(--ink); }
.opt.bad, .opt.wrong { background:var(--pink); color:#fff; }
#btn-board, #btn-home, .quiz-card { background:var(--pink); color:#fff; text-align:center; font-weight:700; }
.summary-big { font-family:var(--font-pixel); font-size:1.5rem; text-align:center; margin:12px 0; color:var(--gold); text-shadow:2px 2px 0 var(--ink); }
.report-item, ol#board-list li, #funfact-text, .badge, .dash-stats .stat, .dash-history li,
.map-hud, .map-node, .mentor-card, .levelup-card {
  background:var(--panel); border:3px solid var(--ink); box-shadow:4px 4px 0 var(--ink); border-radius:4px;
}
```

- [ ] **Step 4: Neutralize leftover gradient-text** — append an override so the old gradient-text
headings render solid (the P1 `h1{background:linear-gradient…}` rule is replaced in Step 3; also
override `.mastery-title`/`.hud-rank` colors to the new palette):

```css
.hud-rank { color:var(--gold); }
.mchip.lv-proficient { background:var(--teal); color:var(--ink); }
.next-card { background:var(--pink); }
```

- [ ] **Step 5: Run the suite + a visual smoke**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add frontend/styles.css
git commit -m "feat(p4a): flat arcade palette + chunky pixel chrome"
```

---

### Task 3: Scanline overlay + pixel numerals

**Files:**
- Modify: `frontend/index.html` (add `#scanline`), `frontend/styles.css` (scanline + pixel numerals)

**Interfaces:**
- Produces: a CRT scanline over the app; numerals/score/HUD level use the pixel font.

- [ ] **Step 1: Add the scanline div to `frontend/index.html`** — right after the opening `<body>`:

```html
<body>
  <div id="scanline"></div>
```

- [ ] **Step 2: Append scanline + pixel-numeral CSS to `frontend/styles.css`**

```css
/* ---- P4a scanline + pixel numerals ---- */
#scanline {
  position:fixed; inset:0; z-index:9998; pointer-events:none;
  background:
    repeating-linear-gradient(transparent 0 2px, rgba(0,0,0,.18) 2px 3px),
    radial-gradient(120% 120% at 50% 50%, transparent 60%, rgba(0,0,0,.35) 100%);
  mix-blend-mode:multiply;
}
.hud-rank, #progress, .summary-big, .levelup-title, .dash-stats .stat b { font-family:var(--font-pixel); }
.dash-stats .stat b { font-size:1rem; }
.hud-rank { font-size:.6rem; }
#progress { font-size:.7rem; color:var(--gold); }
```

- [ ] **Step 3: Ensure interactive overlays sit above the scanline** — the mentor/level-up/avatar
overlays use `z-index:10000+` (already higher than `#scanline`'s `9998`), and `#fx-layer` is
`9999`; confirm no change needed. (Verification only — no edit unless a check fails.)

- [ ] **Step 4: Run the suite**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/styles.css
git commit -m "feat(p4a): CRT scanline overlay + pixel-font numerals"
```

---

### Task 4: Full-suite gate + deploy + screenshot

**Files:** none.

- [ ] **Step 1: Combined suite**

Run: `./scripts/test.sh`
Expected: backend 106; frontend vitest 28; drag e2e passes.

- [ ] **Step 2: Deploy (frontend-only; no reseed/migrate)**

Run: `docker compose up -d --build`
Verify: `curl -s localhost:8000/health` → ok; fonts served:
`curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/app/fonts/PressStart2P-latin.woff2` → `200`;
`curl -s localhost:8000/app/styles.css | grep -c "PressStart2P"` ≥ 1.

- [ ] **Step 3: Screenshot** the new look (onboarding/map/runner) with the puppeteer helper and
review that the arcade theme (flat navy, pink/gold/teal, hard shadows, scanline, pixel numerals)
renders.

---

## Self-Review (completed by plan author)

**Spec coverage (P4a slice of §7):** self-hosted fonts (§4.1) → Task 1 ✓; flat palette + pixel
chrome (§4.3) → Task 2 ✓; CRT scanline (§4.3) → Task 3 ✓; applied across existing components,
frontend-only, IDs preserved → Tasks 2–4 ✓. Sprites (P4b) and level-path map (P4c) are out of
this plan.

**Placeholder scan:** No "TBD/handle later" — the font download script, every CSS block, and the
scanline markup are concrete.

**Type consistency:** Font vars `--font-head/body/pixel` defined in Task 1's `@font-face` + Task 2's
`:root`, consumed in Tasks 2–3. Legacy palette aliases (`--card`, `--accent`, `--good`, `--bad`)
are kept in `:root` so existing P1–P3 rules referencing them stay valid. Keyframe names are
unchanged (`screen-in`, `pop-good`, `node-pulse`, `confetti-fall`), so app/test references hold.

## Out of scope (P4b/P4c)
- `sprites.js` + emoji→SVG sprite replacement (P4b).
- Winding level-path map layout + avatar marker/flags (P4c).
