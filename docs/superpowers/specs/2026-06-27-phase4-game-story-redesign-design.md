# Design Spec — Phase 4: Game Interface + Storytelling Redesign ("رحلة الباحث")

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phases 1–3C (live at src.mulhamfetna.com)

## 1. Purpose

Reskin the Telegram Mini App into a **mentor-guided game journey** — *"رحلة الباحث / The
Researcher's Quest"* — that fuses a journey-map, light RPG progression, a detective-themed
journals stage, and a storytelling mentor. The four quizzes become stages on a path toward
"publishing your first paper."

**Hard constraint: frontend-only.** No backend, API, DB, or content changes. Everything is
computed client-side from existing endpoints, or stored in Telegram CloudStorage.

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Narrative frame | Fusion: journey (spine) + RPG + detective (journals stage) + world-map, unified as "رحلة الباحث". |
| Art | **CSS/SVG + emoji only** — no image assets. |
| Progression | **Soft path** — stages shown in story order with a pulsing "next" marker; all stages remain playable (no hard lock). |
| Storytelling | **Mentor guide** — a named owl-scholar (🦉) speaking short Arabic dialogue bubbles. |
| RPG layer | **All of:** XP + levels, rank titles, boss challenge per stage, avatar customization. |
| Implementation | **Frontend-only (Approach A)** — reuse existing APIs; no backend/DB change. |
| Boss | The **highest-`base_points` question** in each attempt's sample, moved last and reframed (no dedicated boss content). |
| Persistence | Avatar / display name / onboarding-seen flag via **Telegram `CloudStorage`** (localStorage fallback). |

## 3. Architecture (frontend-only)

```
Existing APIs (unchanged):
  GET /api/quizzes                      -> stage list (slug, title_ar) in display order
  GET /api/quizzes/{slug}/questions     -> sampled questions (runner)
  POST /api/quizzes/{slug}/submit       -> report (score, accuracy, earned_now, rank)
  GET /api/me/dashboard                 -> { stats:{total_points,...}, mastery, history, next, badges }

frontend/ (rebuilt):
  game.js      -> pure game logic: XP/level/rank, map state, boss pick, mentor lines
  app.js       -> screens + flow (existing runner/report/board reused, reskinned)
  ui.js        -> reusable UI: mentorSay(), confetti(), levelBar, HUD
  store.js     -> CloudStorage wrapper (get/set avatar, name, flags; localStorage fallback)
  index.html   -> new screens: onboarding, map; reskinned runner/report/board/badges/progress
  styles.css   -> game theme + animations
```

Map/HUD data flow: on load, fetch `/api/quizzes` (stage order) + `/me/dashboard` (per-quiz
best via `stats.best_by_quiz`, total points, badges). Derive level/rank/XP and each stage's
state (done / next / available) **client-side**. No new persisted server state.

## 4. Components

### 4.1 `game.js` — pure logic (unit-tested)
- `levelFromXp(xp) -> {level, rank_ar, intoLevel, span, progress}` — XP = total points; level via
  fixed thresholds (e.g. cumulative `0,200,500,1000,1700,2600,3700,5000,…` — superlinear); `rank_ar`
  from level bands.
- `RANKS = [{minLevel, ar}]` — طالب (Lv1–2) · باحث (3–5) · باحث رئيسي (6–9) · بروفيسور (10+).
- `mapState(quizzes, dashboard) -> [{slug, title_ar, index, status}]` — `status ∈ done|next|open`:
  `done` if `best_by_quiz[slug]` exists; the first non-done stage (in order) is `next`; the rest
  `open` (soft path — all are playable; status is visual only).
- `pickBoss(questions) -> {bossId, ordered}` — choose the max-`base_points` question (ties → last),
  return the question list reordered so the boss is last and a `bossId`.
- `MENTOR` — keyed Arabic lines: `welcome`, `stage[slug]`, `boss`, `levelUp`, `streak`, `victory`,
  `encourage`. `mentorLineFor(key, ctx)` returns the string (with simple `{name}` interpolation).

### 4.2 `store.js` — persistence
- `loadProfile() -> Promise<{name, avatar, onboarded}>` and `saveProfile(partial)`. Uses
  `Telegram.WebApp.CloudStorage` when available (async key/value); falls back to `localStorage`.
- Keys: `rq_name`, `rq_avatar`, `rq_onboarded`.

### 4.3 `ui.js` — reusable visuals
- `mentorSay(text, {onDone})` — renders an owl avatar + typed Arabic bubble; advances on tap.
- `confetti()` / `burst(el)` — CSS/canvas-free particle pop (DOM spans animated via CSS).
- `renderHUD(el, {avatar, name, rank_ar, level, progress})` — the top bar (avatar, rank, level bar).
- `levelUpOverlay(level, rank_ar)` — celebratory overlay used when level increases.

### 4.4 Screens (`index.html` + `app.js`)
- **onboarding** (first run only): mentor welcome → enter display name → pick avatar (emoji grid) →
  save to CloudStorage → go to map. Skipped when `onboarded` is set.
- **map** (home): HUD + path of 4 stage nodes (`done` ✓+glow, `next` pulsing, `open` normal) +
  buttons to badges/dashboard. Tap a node → stage intro.
- **stage intro:** `mentorSay(stage line)` → starts the quiz.
- **runner** (reskinned): existing logic; the boss question (last) gets a "تحدي الزعيم" banner +
  intensified theme + a mentor warning. Journals stage uses detective flavor copy.
- **victory/report** (reskinned): score + stars + `earned_now` badges + mentor victory line +
  confetti; if level increased since the attempt started, show `levelUpOverlay`.
- **board / badges / progress:** reskinned to the theme; logic unchanged.

### 4.5 Level-up detection
Capture `total_points` (→ level) before an attempt; after `submit` returns, recompute level from
`previous_total + report.total_score`; if higher, trigger `levelUpOverlay` + mentor `levelUp` line.

## 5. Theme & motion
A cohesive palette layered over the existing dark base (deep indigo + gold accents, soft glows,
gradients), CSS-only transitions/animations: screen slide/fade, node pulse on the map, level-bar
fill, confetti on correct + victory, streak flare, button press "pop". All emoji/CSS/SVG — no
image assets. The cache-busting in `main.py` auto-versions the new bundle.

## 6. Out of scope (YAGNI / future)
- Any backend/API/DB change; server-persisted XP/avatars; new content or dedicated boss questions.
- Hard stage locking; live multiplayer; sound/music; AI-generated art.
- Changing scoring/sampling/dashboard semantics.

## 7. Testing
- **Vitest (jsdom):** `levelFromXp` (thresholds, rank bands, progress), `mapState`
  (done/next/open from a mock dashboard, soft-path), `pickBoss` (max points last, ties),
  `mentorLineFor` (keys + interpolation), `store` (CloudStorage path + localStorage fallback).
- **Existing guards keep passing:** the runner/fun-fact screen-transition test and the
  `drag.e2e.mjs` browser test (order/match still work after the reskin).
- **Manual:** full playthrough in Telegram (onboarding → map → stage → boss → victory → level-up).

## 8. Decomposition (one spec → phased plan)
- **P1 — Theme & juice:** game palette + animations + reusable `ui.js`/confetti across existing
  screens. Independently shippable; no flow change.
- **P2 — Map, mentor, onboarding:** `store.js`, onboarding, journey map home, mentor bubbles,
  stage intros, `mapState`.
- **P3 — RPG systems:** `game.js` XP/level/rank, HUD, avatar customization, boss reframing,
  level-up overlay.

Each phase ships a working, playable app and gets its own implementation plan.
