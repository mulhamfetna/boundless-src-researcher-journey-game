# Phase 4 · P3 — RPG Systems + Narrative Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the RPG layer — XP/level bar + rank in the map HUD, avatar change, a "boss" final question per stage, and a level-up celebration — and reorder the stages into narrative order.

**Architecture:** Mostly frontend. `game.js` gains pure `levelFromXp`/`RANKS`/`pickBoss`; `ui.js` gains `renderHUD`/`levelUpOverlay`. `app.js` renders the HUD from `/me/dashboard`'s `total_points`, reframes the highest-points question as the boss, and shows a level-up overlay when an attempt pushes the learner up a level. The only non-frontend change is setting `display_order` 1–4 across the four content JSONs (then reseed) so the map reads foundations → paper-parts → paper-types → journals.

**Tech Stack:** Dependency-free HTML/CSS/JS; Vitest + jsdom; the existing `drag.e2e.mjs` browser test; backend reseed for the ordering change.

## Global Constraints

- **Frontend-only except** the content `display_order` edit + reseed (Task 5).
- **XP = `dashboard.stats.total_points`** (already returned by `GET /api/me/dashboard`). Levels via fixed thresholds; ranks: **طالب** (Lv 1–2) · **باحث** (3–5) · **باحث رئيسي** (6–9) · **بروفيسور** (10+).
- **Boss = the highest-`base_points` question** of the attempt's sample (ties → last), moved to the end and visually reframed. No dedicated boss content.
- **Level-up**: compare level from `total_points` before the attempt vs. `total_points + report.total_score` after; if higher, show the overlay.
- **Guard every call into `game.js`/`ui.js` from `app.js` with `typeof`** so `app.js` still evaluates standalone (`runner.test.js` loads `app.js` without the other modules and calls `startQuiz`). Specifically `pickBoss`, `levelFromXp`, `levelUpOverlay`, `renderHUD` must be `typeof`-guarded at their call sites.
- **Arabic, RTL; CSS/SVG/emoji only.** Preserve all existing element IDs/classes.
- **Stage order:** foundations=1, paper-parts=2, paper-types=3, journals=4 in the content files.
- **All existing tests stay green:** `./scripts/test.sh` (pytest 106 + vitest 19 + drag e2e).
- Cache-busting already covers `game.js`/`ui.js` (P2). Tests run from `frontend/`.

---

## File Structure

```
frontend/
  game.js        # MODIFY: levelFromXp, RANKS, rankFor, pickBoss
  ui.js          # MODIFY: renderHUD, levelUpOverlay
  app.js         # MODIFY: HUD on map, currentXp tracking, boss in startQuiz/renderQuestion, level-up in submit, avatar change
  index.html     # MODIFY: #boss-banner in runner
  styles.css     # MODIFY: HUD/boss/levelup styles
  tests/game.test.js   # MODIFY: levelFromXp + pickBoss tests
  tests/ui.test.js     # MODIFY: renderHUD + levelUpOverlay tests
content/questions/{foundations,paper-parts,paper-types,journals}.json  # MODIFY: display_order 1..4
```

---

### Task 1: `game.js` — levels, ranks, boss pick (TDD)

**Files:**
- Modify: `frontend/game.js`, `frontend/tests/game.test.js`

**Interfaces:**
- Produces (on `window`):
  - `levelFromXp(xp) -> {level:int, rank_ar:string, intoLevel:int, span:int, progress:number}` —
    `progress` in `[0,1]`.
  - `RANKS` and `rankFor(level) -> string`.
  - `pickBoss(questions) -> {bossId, ordered}` — `bossId` is the id of the max-`base_points`
    question (ties → last); `ordered` is `questions` with that question moved to the end. Empty
    input → `{bossId:null, ordered:[]}`.

- [ ] **Step 1: Add failing tests** to `frontend/tests/game.test.js` (append)

```javascript
describe("levelFromXp", () => {
  it("xp 0 is level 1, rank طالب, progress in [0,1)", () => {
    const r = window.levelFromXp(0);
    expect(r.level).toBe(1);
    expect(r.rank_ar).toBe("طالب");
    expect(r.progress).toBeGreaterThanOrEqual(0);
    expect(r.progress).toBeLessThan(1);
  });
  it("crossing a threshold raises the level", () => {
    expect(window.levelFromXp(299).level).toBe(1);
    expect(window.levelFromXp(300).level).toBe(2);
  });
  it("high xp reaches بروفيسور", () => {
    expect(window.levelFromXp(100000).rank_ar).toBe("بروفيسور");
  });
  it("handles missing/negative xp", () => {
    expect(window.levelFromXp(undefined).level).toBe(1);
    expect(window.levelFromXp(-50).level).toBe(1);
  });
});

describe("pickBoss", () => {
  it("picks the highest base_points and moves it last", () => {
    const qs = [{ id: 1, base_points: 100 }, { id: 2, base_points: 120 }, { id: 3, base_points: 90 }];
    const { bossId, ordered } = window.pickBoss(qs);
    expect(bossId).toBe(2);
    expect(ordered[ordered.length - 1].id).toBe(2);
    expect(ordered.length).toBe(3);
  });
  it("ties resolve to the last max", () => {
    const qs = [{ id: 1, base_points: 120 }, { id: 2, base_points: 120 }];
    expect(window.pickBoss(qs).bossId).toBe(2);
  });
  it("empty input is safe", () => {
    expect(window.pickBoss([])).toEqual({ bossId: null, ordered: [] });
  });
});
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd frontend && npm test -- game`
Expected: FAIL — `window.levelFromXp is not a function`.

- [ ] **Step 3: Edit `frontend/game.js`** — add inside the IIFE, before the `window.mapState = …` exports:

```javascript
  const THRESHOLDS = [0, 300, 700, 1200, 1900, 2800, 3900, 5200, 6700, 8400]; // cumulative xp for level 1..10
  const RANKS = [{ min: 1, ar: "طالب" }, { min: 3, ar: "باحث" }, { min: 6, ar: "باحث رئيسي" }, { min: 10, ar: "بروفيسور" }];

  function rankFor(level) {
    let r = RANKS[0].ar;
    for (const b of RANKS) if (level >= b.min) r = b.ar;
    return r;
  }
  function levelStart(level) {
    if (level - 1 < THRESHOLDS.length) return THRESHOLDS[level - 1];
    return THRESHOLDS[THRESHOLDS.length - 1] + (level - THRESHOLDS.length) * 2000;
  }
  function levelFromXp(xp) {
    xp = Math.max(0, Number(xp) || 0);
    let level = 1;
    while (xp >= levelStart(level + 1)) level++;
    const start = levelStart(level), next = levelStart(level + 1);
    const span = next - start;
    const intoLevel = xp - start;
    return { level, rank_ar: rankFor(level), intoLevel, span, progress: span > 0 ? intoLevel / span : 0 };
  }
  function pickBoss(questions) {
    if (!questions || !questions.length) return { bossId: null, ordered: [] };
    let boss = questions[0];
    for (const q of questions) if ((q.base_points || 0) >= (boss.base_points || 0)) boss = q;
    const ordered = questions.filter((q) => q !== boss).concat([boss]);
    return { bossId: boss.id, ordered };
  }
```

And add to the exports block:

```javascript
  window.levelFromXp = levelFromXp;
  window.RANKS = RANKS;
  window.rankFor = rankFor;
  window.pickBoss = pickBoss;
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd frontend && npm test -- game`
Expected: PASS (6 P2 + 7 new = 13).

- [ ] **Step 5: Commit**

```bash
git add frontend/game.js frontend/tests/game.test.js
git commit -m "feat(p3): XP levels, ranks, and boss pick (game.js)"
```

---

### Task 2: `ui.js` — HUD + level-up overlay (TDD) + styles

**Files:**
- Modify: `frontend/ui.js`, `frontend/tests/ui.test.js`, `frontend/styles.css`

**Interfaces:**
- Produces (on `window`):
  - `renderHUD(el, s)` — `s = {avatar, name, rank_ar, level, progress}`; sets `el.innerHTML` to a
    HUD with avatar, name, `rank · ★level`, and a `.level-bar > i` filled to `progress*100%`.
  - `levelUpOverlay(level, rank_ar) -> HTMLElement` — celebratory overlay appended to
    `document.body`, fires `confetti` if available, removed on its button click.

- [ ] **Step 1: Add failing tests** to `frontend/tests/ui.test.js` (append)

```javascript
describe("renderHUD", () => {
  beforeEach(() => { loadUi(); });
  it("renders avatar, name, rank/level and a filled level bar", () => {
    const el = document.createElement("div");
    window.renderHUD(el, { avatar: "🦉", name: "لينا", rank_ar: "باحث", level: 4, progress: 0.5 });
    expect(el.querySelector(".hud-name").textContent).toBe("لينا");
    expect(el.textContent).toContain("باحث");
    expect(el.querySelector(".level-bar > i").style.width).toBe("50%");
  });
});

describe("levelUpOverlay", () => {
  beforeEach(() => { loadUi(); });
  it("shows the level and removes on click", () => {
    const ov = window.levelUpOverlay(5, "باحث");
    expect(document.querySelector(".levelup-overlay")).not.toBeNull();
    expect(ov.textContent).toContain("5");
    document.querySelector(".levelup-next").click();
    expect(document.querySelector(".levelup-overlay")).toBeNull();
  });
});
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd frontend && npm test -- ui`
Expected: FAIL — `window.renderHUD is not a function`.

- [ ] **Step 3: Add to `frontend/ui.js`** — inside the IIFE, before the exports block:

```javascript
  function renderHUD(el, s) {
    s = s || {};
    el.innerHTML =
      `<span class="hud-avatar">${s.avatar || "🧑‍🎓"}</span>` +
      `<div class="hud-meta">` +
      `<div class="hud-line"><span class="hud-name">${s.name || "باحث"}</span>` +
      `<span class="hud-rank">${s.rank_ar || ""} · ★${s.level || 1}</span></div>` +
      `<div class="level-bar"><i style="width:${Math.round((s.progress || 0) * 100)}%"></i></div>` +
      `</div>`;
  }

  function levelUpOverlay(level, rank_ar) {
    const ov = document.createElement("div");
    ov.className = "levelup-overlay";
    ov.innerHTML =
      `<div class="levelup-card"><div class="levelup-emoji">⭐</div>` +
      `<div class="levelup-title">المستوى ${level}!</div>` +
      `<div class="levelup-rank">${rank_ar || ""}</div>` +
      `<button class="levelup-next">رائع!</button></div>`;
    ov.querySelector(".levelup-next").onclick = () => ov.remove();
    document.body.appendChild(ov);
    if (typeof confetti === "function") confetti({ count: 40 });
    return ov;
  }
```

And add to the exports block: `window.renderHUD = renderHUD; window.levelUpOverlay = levelUpOverlay;`

- [ ] **Step 4: Append HUD + level-up styles to `frontend/styles.css`**

```css
/* ---- P3 HUD + boss + level-up ---- */
.map-hud .hud-meta { flex:1; }
.hud-line { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.hud-rank { color:var(--gold); font-size:.85rem; font-weight:700; }
#boss-banner { text-align:center; font-weight:800; color:#1a1330; padding:8px; border-radius:12px;
  margin-bottom:8px; background:linear-gradient(90deg,var(--gold),#ffb703); animation:pop-good .4s ease; }
#screen-runner.boss .opt { box-shadow:0 0 0 1px #ffd16655, 0 2px 0 #0006; }
.levelup-overlay { position:fixed; inset:0; z-index:10001; display:flex; align-items:center;
  justify-content:center; background:#000b; }
.levelup-card { text-align:center; padding:28px 24px; border-radius:20px; max-width:340px; width:86%;
  background:linear-gradient(180deg,var(--card2),var(--card)); box-shadow:0 0 60px #7c5cff66; animation:screen-in .3s ease; }
.levelup-emoji { font-size:3rem; }
.levelup-title { font-size:1.6rem; font-weight:800; margin:6px 0;
  background:linear-gradient(90deg,var(--gold),#fff3c4); -webkit-background-clip:text; background-clip:text; color:transparent; }
.levelup-rank { color:var(--muted); margin-bottom:14px; }
```

- [ ] **Step 5: Run ui tests, expect pass**

Run: `cd frontend && npm test -- ui`
Expected: PASS (6 P1/P2 + 2 new = 8).

- [ ] **Step 6: Commit**

```bash
git add frontend/ui.js frontend/tests/ui.test.js frontend/styles.css
git commit -m "feat(p3): HUD level bar + level-up overlay (ui.js)"
```

---

### Task 3: HUD on the map + level-up + avatar change (app.js)

**Files:**
- Modify: `frontend/app.js`

**Interfaces:**
- Consumes: `levelFromXp`, `renderHUD`, `levelUpOverlay` (guarded), `loadProfile`/`saveProfile`, `AVATARS`.
- Produces: the map HUD shows level/rank/XP; a module var `currentXp` tracks total points; finishing
  an attempt that crosses a level shows the overlay; tapping the HUD avatar opens a picker.

- [ ] **Step 1: Add a module-level `currentXp` and update `renderMap`** — replace the `renderMap`
function's HUD block. Add near the top of `app.js` (after the `state` declaration):

```javascript
let currentXp = 0;
```

In `renderMap`, replace the `const hud = …; hud.innerHTML = …;` block with:

```javascript
  currentXp = (dashboard && dashboard.stats && dashboard.stats.total_points) || 0;
  const hud = document.getElementById("map-hud");
  if (typeof renderHUD === "function" && typeof levelFromXp === "function") {
    const lv = levelFromXp(currentXp);
    renderHUD(hud, { avatar: profile.avatar, name: profile.name, rank_ar: lv.rank_ar, level: lv.level, progress: lv.progress });
    const av = hud.querySelector(".hud-avatar");
    if (av) av.onclick = () => openAvatarPicker(profile);
  } else {
    hud.innerHTML = `<span class="hud-avatar">${profile.avatar}</span><span class="hud-name">${profile.name || "باحث"}</span>`;
  }
```

- [ ] **Step 2: Add `openAvatarPicker`** — place it after `showOnboarding` in `app.js`:

```javascript
function openAvatarPicker(profile) {
  const ov = document.createElement("div");
  ov.className = "mentor-overlay";
  ov.innerHTML = `<div class="mentor-card"><div class="mentor-text">اختر رمزك</div><div class="ob-avatars"></div></div>`;
  const grid = ov.querySelector(".ob-avatars");
  AVATARS.forEach((a) => {
    const b = document.createElement("span");
    b.className = "ob-avatar" + (a === profile.avatar ? " selected" : "");
    b.textContent = a;
    b.onclick = async () => {
      profile.avatar = a;
      await saveProfile({ avatar: a });
      ov.remove();
      renderMap(profile);
    };
    grid.appendChild(b);
  });
  ov.addEventListener("click", (e) => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}
```

- [ ] **Step 3: Add level-up detection in `submit`** — in `frontend/app.js`'s `submit`, after
`renderReport(report);` and before `show("report");`, add:

```javascript
  if (typeof levelFromXp === "function" && typeof levelUpOverlay === "function") {
    const before = levelFromXp(currentXp).level;
    const afterLv = levelFromXp(currentXp + (report.total_score || 0));
    currentXp += report.total_score || 0;
    if (afterLv.level > before) levelUpOverlay(afterLv.level, afterLv.rank_ar);
  }
```

- [ ] **Step 4: Verify standalone + suite**

Run: `cd frontend && node --check app.js && npm test && node tests/drag.e2e.mjs`
Expected: syntax OK; vitest passes (`runner.test.js` unaffected — `renderMap`/`submit`/`openAvatarPicker`
guards mean no undefined-global execution in the tested `startQuiz`/`nextStep` paths; `submit` isn't
reached by those tests anyway); drag e2e passes.

- [ ] **Step 5: Commit**

```bash
git add frontend/app.js
git commit -m "feat(p3): map HUD (level/rank/xp), level-up overlay, avatar picker"
```

---

### Task 4: Boss question reframing

**Files:**
- Modify: `frontend/index.html` (boss banner in runner), `frontend/app.js` (`startQuiz` boss pick, `renderQuestion` boss UI)

**Interfaces:**
- Consumes: `pickBoss` (guarded). Produces: the highest-points question runs last with a
  "👑 تحدّي الزعيم" banner and a boss theme class on `#screen-runner`.

- [ ] **Step 1: Add the boss banner to `frontend/index.html`** — inside `#screen-runner`, right
after the `<div class="topbar">…</div>` block and before `<h2 id="q-prompt">`:

```html
      <div id="boss-banner" class="hidden">👑 تحدّي الزعيم</div>
```

- [ ] **Step 2: Pick the boss in `startQuiz`** — in `frontend/app.js`, replace the `state = { … }`
assignment inside `startQuiz` with a boss-aware version:

```javascript
async function startQuiz(slug) {
  const data = await api(`/quizzes/${slug}/questions`);
  const picked = (typeof pickBoss === "function") ? pickBoss(data.questions) : { bossId: null, ordered: data.questions };
  state = { slug, questions: picked.ordered, bossId: picked.bossId, funFacts: data.fun_facts_ar || [], idx: 0, answers: [], startedAt: Date.now() };
  renderQuestion();
  show("runner");
}
```

- [ ] **Step 3: Toggle the boss UI in `renderQuestion`** — in `frontend/app.js`, at the start of
`renderQuestion` (right after `show("runner");` added in P1), add:

```javascript
  const isBoss = state.bossId != null && state.questions[state.idx] && state.questions[state.idx].id === state.bossId;
  const bossBanner = document.getElementById("boss-banner");
  if (bossBanner) bossBanner.classList.toggle("hidden", !isBoss);
  document.getElementById("screen-runner").classList.toggle("boss", isBoss);
```

- [ ] **Step 4: Verify standalone + suite**

Run: `cd frontend && node --check app.js && npm test && node tests/drag.e2e.mjs`
Expected: syntax OK; `runner.test.js` passes — `pickBoss` is guarded, so without `game.js` the
ordered list equals `data.questions` (unchanged behavior); the boss banner toggling is null-safe.
drag e2e passes.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/app.js
git commit -m "feat(p3): boss final question (banner + reorder + theme)"
```

---

### Task 5: Narrative stage ordering (content)

**Files:**
- Modify: `content/questions/foundations.json` (`display_order:1`), `paper-parts.json` (`2`), `paper-types.json` (`3`), `journals.json` (`4`)

**Interfaces:**
- Produces: `/api/quizzes` returns stages in story order after reseed.

- [ ] **Step 1: Set `display_order` in each content file.** Each quiz doc has a top-level
`"display_order"` field. Set:
- `content/questions/foundations.json` → `"display_order": 1`
- `content/questions/paper-parts.json` → `"display_order": 2`
- `content/questions/paper-types.json` → `"display_order": 3`
- `content/questions/journals.json` → `"display_order": 4` (already 4? it is currently `1` — change to `4`)

Use a small script to set them precisely:

```bash
cd /mnt/data/projects/Boundless/Gamified-sessions && python3 - <<'PY'
import json
order = {"foundations":1, "paper-parts":2, "paper-types":3, "journals":4}
for slug, n in order.items():
    p = f"content/questions/{slug}.json"
    d = json.load(open(p, encoding="utf-8"))
    d["display_order"] = n
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(slug, "->", n)
PY
```

- [ ] **Step 2: Validate the files**

Run:
```bash
cd backend && for f in foundations paper-parts paper-types journals; do python3 -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/$f.json',encoding='utf-8'))); print('ok','$f')"; done
```
Expected: `ok` ×4.

- [ ] **Step 3: Commit**

```bash
git add content/questions/
git commit -m "content(p3): narrative stage order (foundations→parts→types→journals)"
```

---

### Task 6: Full-suite gate + deploy + reseed

**Files:** none (verification/deploy).

- [ ] **Step 1: Combined suite**

Run: `./scripts/test.sh`
Expected: backend 106; frontend vitest (runner 3 + ui 8 + store 4 + game 13 = 28); drag e2e passes.

- [ ] **Step 2: Deploy + reseed** (the ordering change needs a reseed; resets test leaderboards)

Run:
```bash
docker compose up -d --build
sleep 3
docker compose exec -T web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_all; c=connect('/data/quiz.db'); init_schema(c); print(seed_all(c,'/srv/content/questions'))"
```
Expected: prints the seeded slugs.

- [ ] **Step 3: Verify**

Run:
```bash
curl -s localhost:8000/health
curl -s localhost:8000/api/quizzes | python3 -c "import sys,json; print([q['slug'] for q in json.load(sys.stdin)])"
curl -s localhost:8000/app/game.js | grep -c levelFromXp
```
Expected: health ok; quizzes in order `['foundations','paper-parts','paper-types','journals']`;
`game.js` contains `levelFromXp`.

---

## Self-Review (completed by plan author)

**Spec coverage (P3 slice of §8 + §4):** XP/level/rank HUD (§4.1 `levelFromXp`/`RANKS`, §4.4 HUD) →
Tasks 1, 2, 3 ✓; avatar customization (pick + later change) → Task 3 `openAvatarPicker` ✓; boss
challenge per stage (§4.1 `pickBoss`, §4.4 runner) → Tasks 1, 4 ✓; level-up overlay (§4.5) →
Tasks 2, 3 ✓; narrative ordering (folded-in request) → Task 5 ✓.

**Placeholder scan:** No "TBD/handle later" — every function, test, CSS block, and the content edit
script are concrete.

**Type consistency:** `levelFromXp(xp)->{level,rank_ar,progress,…}` (Task 1) matches `renderHUD`
input and the level-up compare (Tasks 2, 3). `pickBoss(questions)->{bossId,ordered}` (Task 1)
matches `startQuiz`/`renderQuestion` usage (Task 4). `renderHUD(el,s)`/`levelUpOverlay(level,rank_ar)`
(Task 2) match the calls in Task 3. `currentXp` is set in `renderMap` and read in `submit` (Task 3).
All `app.js`→module calls (`pickBoss`, `levelFromXp`, `renderHUD`, `levelUpOverlay`) are
`typeof`-guarded per the constraint, keeping `runner.test.js` green.

## Out of scope (future)
- Server-persisted XP; multiplayer; sound; avatar travelling animation along the path (HUD avatar +
  per-node markers are the P3 surface).
