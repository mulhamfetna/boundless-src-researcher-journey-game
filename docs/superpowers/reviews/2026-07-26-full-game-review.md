# Full Game Review — رحلة الباحث (curated)

**Date:** 2026-07-26 · Drafted with agy (Gemini), **curated + verified inline** against the live game/engine.
Scope: scientific rigor, content enrichment, gamification. Grounded in the current state (6 application-first stations + Capstone; types mcq/tf/image/match/order/spot; XP/level/streak/boss/5 badges/leaderboards/mastery dashboard/Arcane art; vanilla-JS + SQLite + Telegram, client-side scoring).

## A. Scientific — accuracy & coverage

**Already handled well (do NOT re-add):** Green/Gold/Diamond/Hybrid OA (journals), ICMJE authorship vs acknowledgments (publishing), fake-metric / "Universal Impact Factor" audit + quartiles + multi-metric (journals), predatory-journal red flags (journals + capstone), power analysis + ANCOVA (capstone).

**Genuine high-value gaps (verified accurate, worth adding):**
1. **Statistics literacy** — the biggest gap. p‑value ≠ effect size ≠ practical significance; **p‑hacking, HARKing, pre-registration, data dredging**. (Only *power analysis* exists today.) → foundations + capstone.
2. **AI/LLMs in research** — modern & missing. Per COPE/ICMJE an LLM **cannot be an author**; teach disclosure, hallucinated-reference auditing, permissible use. → publishing.
3. **Reporting guidelines (EQUATOR)** — **STROBE** (observational), **PRISMA** (reviews), **CONSORT** (RCTs). Missing; journals reject papers without them. → paper-parts / paper-types / capstone.
4. **ORCID & author disambiguation** — especially valuable for Arabic name transliteration. Missing. → publishing/submission.
5. **Causation vs association framing** — the capstone cohort study should phrase conclusions as *risk/association + residual confounding*, not "dust *causes* damage". Low-effort explanation tweak. → capstone.

**Nice-to-have depth:** open science / preprints (arXiv-bioRxiv-medRxiv) / FAIR data; **hijacked/cloned journals** & predatory *conferences* (journals already does predatory journals); coercive-citation / self-citation cartels (partially in journals).

## B. Content enrichment

- **Tiered difficulty** (Zaun basic-audit → Promenade spot-flaws → Piltover high-stakes editorial). The game varies *mood* by level (world-lerp) but not *task difficulty*; a difficulty tag + progression would deepen it. Medium effort.
- **Concrete new tasks (all buildable on the current engine):**
  - `spot` **AI-authorship audit** — a contributions statement crediting "ChatGPT-4o as co-author" → flag the violation (COPE: no accountability). 
  - `match` **p‑hacking/HARKing** — bad practice → its name → its remedy (HARKing→pre-registration; sample-dredging→a priori power analysis).
  - `image` **PRISMA flow audit** — a flowchart missing "reasons for exclusion" at full-text → tap the faulty box. *(Needs a mock PRISMA image asset — can generate one.)*
  - `match` **reporting guideline → study design** (STROBE↔observational, PRISMA↔review, CONSORT↔RCT).
- **Capstone enrichment:** add a STROBE-checklist step and an **ethics/funding dilemma** (accept private funding that hides raw data vs. FAIR/open-data) as an mcq. Enriches without needing v2 branching.
- **More real artifacts:** we now use real screenshots in 5 stations; remaining assets (transformer_intro/discussion, em_login/orcid/general, survey_challenge) can seed more image tasks.

## C. Gamification (grounded in the vanilla-JS + Telegram stack)

**Quick wins (low effort, mostly frontend / small backend):**
- **Expanded badges (5 → ~12–15):** "all stations cleared", "flawless station (no hints)", "red-flag hunter (N spots)", "capstone perfectionist". Award logic lives in `badges.py` + sprites. *Low.*
- **Capstone certificate:** on finishing the journey, a personalized shareable card/PDF (Canvas) with name + rank + a verification hash. High extrinsic pull for students. *Low–med (frontend Canvas + a stored hash).*
- **Lab-Notebook / shareable summary card:** Canvas card of the player's rank, mastery %, capstone "paper" — shared into Telegram study groups via WebApp share. Drives organic growth. *Low–med, pure frontend.*
- **Daily "Hex-Recall" (spaced repetition):** 3 daily questions pulled from the player's weakest concepts (mastery dashboard already tracks these). Fights forgetting. *Med (per-user review state).*

**Bigger (backend/state, higher engagement):**
- **Async "Peer-Review Duel":** Telegram deep-link (`startapp=duel_…`) challenges a colleague to the same desk-review under a timer; bot DMs the winner. Viral in academic groups. *Med (a `duels` table + deep-link).* (This is the async form of the old live-mode idea.)
- **Seasonal leagues:** monthly leaderboard reset with tiers (Zaun Scavenger → High Council Dean). Keeps late-comers motivated. *Med (monthly aggregation).*
- **Skill tree:** branching path (Quant/Stats · Qual/Reviews · Publishing/Ethics). Nice autonomy, but **partly redundant** with the existing winding map — lower priority.

## Recommended order (impact × effort)
1. **Sprint 1 — Science (highest value):** add statistics-literacy (p‑value/effect-size/p‑hacking/HARKing) + AI-authorship + reporting-guidelines tasks; add the causation-vs-association tweak + STROBE step to the capstone. Pure content, reuses the engine.
2. **Sprint 2 — Quick gamification wins:** expanded badges + capstone certificate + shareable Lab-Notebook card.
3. **Sprint 3 — Engagement systems:** daily spaced-repetition, then async duels / seasonal leagues.

Skip/deprioritize: full skill-tree (redundant with the map).
