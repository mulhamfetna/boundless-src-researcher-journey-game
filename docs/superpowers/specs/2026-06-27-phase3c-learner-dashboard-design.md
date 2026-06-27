# Design Spec — Phase 3C: Khan-Style Learner Dashboard

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phases 1, 2A, 2B, 3A, 3B (live at src.mulhamfetna.com)

## 1. Purpose

Give each contestant a personal "تقدّمي" (My Progress) dashboard in the Mini App that shows,
in one place:

1. **Concept mastery map** — per-concept mastery level (the Khan signature), from first-try accuracy.
2. **Progress & stats** — total points, attempts, best scores, best streak, accuracy, hints used.
3. **Activity history** — a timeline of past attempts.
4. **What to do next** — nudges toward the learner's weakest concepts and which quiz to practice.

All data already exists (attempts, answers with `retries`/`hint_used`/`is_correct`, badges, and
per-question `concept` from Phase 3B). Phase 3C is an aggregation + presentation layer; no new
gameplay and no DB schema change.

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Dashboard content | All four: mastery map, progress & stats, activity history, what-to-do-next. |
| Mastery metric | **First-try accuracy** per concept (`first_try = retries == 0 and not hint_used`). |
| Recency window | **Most recent N = 5** answers per concept (current ability, improves with practice). |
| Mastery levels (4) | `not_started` (0 answers) · `familiar` (rate < 0.50) · `proficient` (0.50 ≤ rate < 0.85) · `mastered` (rate ≥ 0.85 **and** ≥ 3 recent answers). |
| Compute location | **Server-side**, recompute-on-read (no materialized table). |
| Concept labels | Slug→Arabic map kept **in code** (`progress.CONCEPT_LABELS_AR`) for now. |
| Surface | **One new Mini App screen** (`screen-progress`), opened from a home button. |
| Auth | `GET /api/me/dashboard` authenticated via Telegram `initData` (like `/me/badges`). |

## 3. Architecture

```
answers + attempts + questions(concept) + badges   (existing tables)
        │  models.get_contestant_answers / get_contestant_attempts
        ▼
app/progress.py  (pure)
  mastery_for_concepts(answers, recent_n=5) -> per-concept level
  summarize_stats(attempts) -> totals
  next_steps(mastery, quiz_of_concept) -> weakest-concept nudges
  CONCEPT_LABELS_AR: slug -> Arabic label
        │
GET /api/me/dashboard  (auth initData)
  -> {stats, mastery[], history[], next[], badges[]}
        │
Mini App screen-progress (RTL): stats header · mastery grid by quiz · "ما التالي؟" · activity list
```

## 4. Components

### 4.1 `app/progress.py` (pure functions, no DB)
- `first_try_of(answer) -> bool` — `answer["retries"] == 0 and not answer["hint_used"]`.
- `mastery_for_concepts(answers: list[dict], recent_n: int = 5) -> dict[str, dict]`
  - Each `answer` carries `concept`, `retries`, `hint_used`, and an `order` (recency rank;
    higher = more recent). Group by `concept`; within a concept keep the most recent `recent_n`
    by `order`; `rate = first_try_count / kept_count`.
  - `level`: `not_started` if no answers; else `mastered` if `rate >= 0.85 and kept_count >= 3`;
    else `proficient` if `rate >= 0.50`; else `familiar`.
  - Returns `{concept: {"rate": float, "count": int, "level": str}}`.
- `level_for(rate: float, count: int) -> str` — the threshold function above (extracted for testing).
- `summarize_stats(attempts: list[dict]) -> dict` — `{total_points, attempts_count,
  best_by_quiz: {slug: best_score}, best_streak, first_try_accuracy}`
  (`first_try_accuracy` = mean of attempts' `accuracy`; empty input → all zeros).
  Note: `hints_used` is NOT here — `attempts` has no hint column; it's computed from the
  answer set in the endpoint (§4.3).
- `next_steps(mastery: dict, quiz_of_concept: dict[str, dict]) -> list[dict]` — pick up to 2
  concepts to improve: lowest `rate` among answered concepts first, then any `not_started`
  concept; each item `{concept, label_ar, quiz_slug, quiz_title_ar, level}`.
- `CONCEPT_LABELS_AR: dict[str, str]` — Arabic label for every concept slug in the 4 quizzes
  (predatory_signs, indexing, quartiles, metrics, open_access, journal_selection,
  methodology_basics, originality, research_gap, gap_types, finding_gaps, choosing_type,
  original_research, review_types, secondary_research, special_formats, title, abstract,
  keywords, introduction, methods, results, discussion, references, structure). A slug missing
  from the map falls back to the slug itself.

### 4.2 `app/models.py` (new queries)
- `get_contestant_answers(conn, contestant_id) -> list[dict]` — join `answers → attempts →
  questions` for finished attempts; each row `{concept (from data_json), retries, hint_used,
  quiz_id, quiz_slug, order}` where `order` ranks by `(attempts.finished_at, answers.id)`.
  Concept is read from `data_json` in Python (no JSON1 dependency).
- `get_contestant_attempts(conn, contestant_id) -> list[dict]` — finished attempts newest first:
  `{quiz_slug, quiz_title_ar, total_score, accuracy, max_streak, finished_at}`.
- `quiz_of_concept(conn) -> dict[str, dict]` — map each concept slug → `{quiz_slug,
  quiz_title_ar}` (a concept belongs to one quiz). Used by `next_steps` and grouping.

### 4.3 `app/api.py`
- `GET /api/me/dashboard` — validate `initData` (401 on failure / no user), then:
  - `answers = models.get_contestant_answers(conn, uid)`
  - `mastery = progress.mastery_for_concepts(answers)`, enriched per concept with `label_ar`,
    `quiz_slug`, `quiz_title_ar` from `quiz_of_concept`; includes every concept of every quiz
    (concepts with no answers appear as `not_started`).
  - `stats = progress.summarize_stats(models.get_contestant_attempts(conn, uid))`, then add
    `stats["hints_used"] = sum(1 for a in answers if a["hint_used"])`
  - `history = ` the attempts list (cap latest 15)
  - `next = progress.next_steps(mastery, quiz_of_concept)`
  - `badges = badges.get_badges(conn, uid)`
  - Response: `{stats, mastery: [...], history: [...], next: [...], badges: [...]}`.

### 4.4 Frontend (`frontend/index.html`, `app.js`, `styles.css`)
- New `screen-progress` (RTL) with: a **stats header** (points, attempts, accuracy, best streak),
  a **mastery grid grouped by quiz** (concept chips colored by level —
  grey=not_started, amber=familiar, blue=proficient, green=mastered), a **"ما التالي؟"** nudge
  card listing `next` items with a button that jumps into that quiz, and a **recent-activity**
  list from `history`. Opened by a "تقدّمي 📊" button on `screen-home`; reuses the existing
  `api()` fetch + `Telegram.WebApp.initData` header pattern; a back button returns home.

## 5. Mastery rules (exact)

- An answer is **first-try** iff `retries == 0` and `hint_used` is falsy.
- Per concept: take the most recent `5` answers; `rate = first_try / kept`.
- `mastered`: `rate ≥ 0.85` AND `kept ≥ 3`. `proficient`: `rate ≥ 0.50`. `familiar`: `rate > 0`
  or `kept ≥ 1` with `rate < 0.50`. `not_started`: no answers for that concept.

## 6. Out of scope (YAGNI / future)
- Materialized/precomputed mastery; time-series charts; decay weighting beyond the recent-N window.
- Cross-learner comparison (the leaderboard already covers ranking).
- Moving concept labels into content JSON (kept in code this phase).
- Bot-side dashboard (Mini App screen only).

## 7. Testing
- `progress.level_for` / `mastery_for_concepts`: each level boundary (0, <0.5, 0.5, 0.85 with
  <3 and ≥3 answers), recency window (only last 5 count; older mistakes drop off), not_started,
  multi-concept input.
- `summarize_stats`: totals, best-by-quiz, best streak, accuracy mean, empty input → zeros.
- `next_steps`: picks lowest-rate concept; falls back to a not_started concept; caps at 2.
- `models.get_contestant_answers` / `get_contestant_attempts`: correct join, recency order,
  concept extracted from `data_json`, only finished attempts.
- API: `/me/dashboard` returns 401 without valid `initData`; with a seeded contestant + attempts,
  returns the documented shape and a mastered concept where expected.
- Frontend: manual playthrough in Telegram.

## 8. Decomposition
One implementation plan: (1) `progress.py` mastery/stats/next + labels (TDD), (2) model queries
(TDD), (3) `/me/dashboard` endpoint (TDD), (4) frontend `screen-progress`. No DB migration; deploy
is rebuild → up (no reseed needed — Phase 3C reads existing data).
