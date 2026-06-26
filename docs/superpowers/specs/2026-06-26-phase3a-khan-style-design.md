# Design Spec — Phase 3A: Khan-Style Question Experience

**Date:** 2026-06-26
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phases 1, 2A, 2B (live at `https://src.mulhamfetna.com`; 4 quizzes,
51 questions). This is the first of three Phase-3 sub-projects (3A foundation →
3B bank scale-up + applied questions → 3C learner dashboard).

## 1. Purpose

Make answering a learning experience, not a one-shot test: immediate per-option
feedback, retry-until-correct without revealing the answer, hints, fun facts,
and scoring that rewards first-try mastery. This phase reshapes the question
schema and the runner so the larger applied question bank (3B) can be authored
against the new shape.

## 2. Confirmed decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Wrong-answer flow | Explain the chosen wrong option; **retry unlimited** until correct; **never reveal** the correct option early |
| Scoring | Points **degrade per retry + per hint**; first-try-no-hint = full |
| Match/order feedback | On submit, **highlight wrong pairs/positions**; fix + resubmit until all correct |
| Existing 51 questions | **Retrofit now** with per-option explainers + hints |
| Fun facts | After **every 5** questions |
| Answer checking | **Client-side** — `GET /questions` ships answer keys + explainers; client runs the retry loop; `submit` reports retries/hints |
| Speed bonus | **Dropped** (timing meaningless with retries) |
| Synthetic data | **Allowed**, marked illustrative where used |

## 3. Schema additions

**Per question** (`data_json`):
- `option_explanations_ar: [str, ...]` — for `mcq`/`tf`/`image`, one entry per option (why that option is wrong; for the correct option, a confirming note). Length MUST equal `options_ar` length when present.
- `hint_ar: str` — optional single hint.
- `match`/`order` need no per-option text (the client highlights wrong elements from the answer key) but may carry `hint_ar`.

**Per quiz:**
- `fun_facts_ar: [str, ...]` — illustrative/teaching facts shown after each group of 5 questions (cycled if fewer than groups).

All validated by `app.content_schema.validate_quiz`.

## 4. Data model (migration — `app/migrate.py`, idempotent)

- `answers`: add `retries INTEGER NOT NULL DEFAULT 0`, `hint_used INTEGER NOT NULL DEFAULT 0`.
- `quizzes`: add `fun_facts_json TEXT NOT NULL DEFAULT '[]'`.
- `db.py` `SCHEMA` updated to include these for fresh installs; `migrate()` adds them to existing DBs (column-existence guarded).
- No badge schema change (badge codes are strings; see §7).

## 5. API changes (`app/api.py`)

- `GET /quizzes/{slug}/questions` additionally returns, per question: the answer key (`correct_index` for mcq/tf/image, `correct_pairs` for match, `correct_sequence` for order), `option_explanations_ar`, `hint_ar`; and at the quiz level `fun_facts_ar`. (Answer-key exposure is the accepted client-side-checking tradeoff.)
- `POST /quizzes/{slug}/submit` answer objects become `{question_id, retries, hint_used}` (the final answer is always correct because the client only advances on solve). The server:
  - `points = round(base_points × penalty × streak_multiplier(streak_before))`, `penalty = max(0.10, 1 − 0.25·retries − 0.20·(1 if hint_used else 0))`.
  - `first_try = (retries == 0 and not hint_used)`; streak advances only on `first_try`; `is_correct` stored as `True` (solved); `retries`/`hint_used` persisted on the answer row.
  - `accuracy = first_try_count / total_questions`.
  - badges via the updated rules; auto-DM unchanged (BackgroundTasks).

## 6. Scoring module (`app/scoring.py`)

Add `retry_penalty(retries: int, hint_used: bool) -> float` = `max(0.10, 1 − 0.25*retries − 0.20*(1 if hint_used else 0))`, and `score_retry(base_points, retries, hint_used, streak_before) -> int` = `round(base_points * retry_penalty(...) * streak_multiplier(streak_before))`. The old `score_answer`/`score_fraction`/`speed_bonus`/`grade` remain (used by tests / not removed), but `submit` uses `score_retry`. `grade` is still used to *validate* that match/order final answers are full before scoring (defense), but the client guarantees a solved state.

## 7. Badges (`app/badges.py`)

- `perfect_quiz` — `accuracy >= 1.0` (all first-try, no hint).
- `streak_master` — `max_streak >= 5`.
- `first_finish` — first finished attempt.
- **`self_reliant`** (replaces `speed_demon`) — `hints_used_total == 0` for the attempt. Arabic label "بلا تلميحات". `evaluate(summary)` now reads `summary["hints_used"]` instead of `avg_speed_bonus`. `ALL_CODES` and `_PRIORITY` updated (`perfect_quiz > streak_master > self_reliant > first_finish`). The frontend `BADGES` map + `report._BADGE_AR` updated to match.

## 8. Runner UX (`frontend/`)

- **mcq/tf/image:** tapping an option that is wrong → mark it red, show `option_explanations_ar[i]`, disable it, increment `retries`; tapping the correct option → green + its confirming explainer → advance. The correct option is never visually distinguished before selection.
- **match/order:** arrange → "تأكيد" → compare to the key client-side; wrong pairs/positions flash red and reset (correct ones lock green), increment `retries`; resubmit until all correct. The correct arrangement is never shown.
- **تلميح** button reveals `hint_ar` and sets `hint_used=true` for that question.
- **Fun facts:** after every 5 answered questions, show a fun-fact card (from the quiz's `fun_facts_ar`, cycled) with a continue button.
- On finish, `submit` sends `[{question_id, retries, hint_used}]`. The report screen shows per-question tries/hint and earned badges (now including `self_reliant`).

## 9. Content retrofit

Add `option_explanations_ar` (one per option) + `hint_ar` to **all 51 existing questions** across the 4 quiz files, and `fun_facts_ar` to **all 4 quizzes**. Grounded in the taught concepts; synthetic where the PDF doesn't supply an explanation, marked illustrative. Each file must still pass `validate_quiz`.

## 10. Testing

- **TDD:** `retry_penalty`/`score_retry` (first-try full, per-retry and per-hint degradation, 10% floor); badges `evaluate` with `self_reliant`/hints; `content_schema` for `option_explanations_ar` length + `hint_ar` + quiz `fun_facts_ar`; migration idempotency (new columns); API submit with retries/hints producing correct points + badges; `get_questions` exposes the new fields.
- Frontend: `node --check` + manual playthrough (wrong→explainer→retry→correct; hint; match/order wrong-highlight; fun-fact card every 5).

## 11. Out of scope (later sub-projects)

- **3B:** large applied/synthetic question bank + random per-attempt sampling (no-repeat).
- **3C:** Khan-Academy-style learner dashboard.
- No change to auth, hosting, or the Cloudflare deploy.
