# Design Spec — Phase 2A: Game Mechanics

**Date:** 2026-06-26
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phase 1 (live at `https://src.mulhamfetna.com`). See
`docs/superpowers/specs/2026-06-25-telegram-gamified-quiz-design.md` and
`docs/superpowers/plans/2026-06-25-phase1-vertical-slice.md`.

## 1. Purpose

Enrich the existing `journals` quiz with the remaining game mechanics, on the
same Telegram Mini App + FastAPI + SQLite stack. This phase adds **no new
quizzes** (the 3 remaining PDFs are Phase 2B). It delivers:

- **match** and **order** question types (drag-and-drop on touch).
- **Partial-credit** scoring for those types.
- **Badges** (4) — awarded, persisted, and surfaced in 4 places.
- An **overall leaderboard** (cross-quiz aggregation).
- **Auto-DM** of the report to each contestant from the backend.

## 2. Confirmed decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Sequence | Mechanics first; new content (3 quizzes) is a later phase |
| Match/order interaction | **Drag-and-drop**, implemented with **pointer events** (touch + mouse), no external lib |
| Match/order scoring | **Partial credit**; streak & accuracy count it correct only at 100% |
| Badges | `perfect_quiz`, `speed_demon`, `streak_master`, `first_finish` |
| Badge display | End-of-quiz report, bot DM, leaderboard rows, dedicated "my badges" screen |
| Overall leaderboard | **Sum of each contestant's best score per quiz** |
| Auto-DM mechanism | **Backend** posts `sendMessage` (it holds `BOT_TOKEN`); fire-and-forget |
| Type CHECK constraint | **Dropped**; validation moves fully to app-level `content_schema` |

## 3. Ground truth in the current code (verified)

- `badges` table exists but **no badge logic anywhere** — net-new.
- Streak is computed transiently in `app/api.py` `submit` (`streak = streak+1 if is_correct else 0`) but never persisted or used.
- `app/scoring.py` has `speed_bonus`, `streak_multiplier`, `score_answer(base, is_correct, time_ms, streak_before)`.
- Leaderboard is per-quiz only (`models.leaderboard`, `GET /api/leaderboard?slug=`); no overall/scope.
- Frontend screens: `home`, `runner`, `report`, `board`. The runner renders prompt + optional image + option buttons only — match/order rendering is net-new.
- `submit` returns the report to the Mini App; there is no bot DM.
- `questions.type` has `CHECK (type IN ('mcq','tf','image'))`.

## 4. Data model changes

1. **Drop the `type` CHECK** on `questions` and add `max_streak` to `attempts`,
   via a migration module (`app/migrate.py`). SQLite cannot alter a CHECK in
   place, so the migration uses the safe table-rebuild ("12-step") pattern with
   `PRAGMA foreign_keys=OFF` around it, preserving rows and ids (so
   `answers.question_id` FKs stay valid). It is idempotent (checks
   `PRAGMA table_info`/a schema marker before acting).
2. **`badges`**: add `UNIQUE(contestant_id, code)` so each badge is awarded once
   (the rebuild/migration adds the index if absent).
3. Question payloads stay in the existing `data_json` text column:
   - `match`: `{"left_ar": [...], "right_ar": [...], "correct_pairs": [[li, ri], ...]}`
   - `order`: `{"items_ar": [...], "correct_sequence": [i0, i1, ...]}`
   - existing `mcq`/`tf`/`image`: `{"options_ar": [...], "correct_index": n}` (unchanged).

The live deployment runs `python -m app.migrate` once, then re-seeds
(`seed_from_file`, idempotent on slug).

## 5. Scoring — `app/scoring.py`

New pure functions (TDD):

- `grade(qtype: str, data: dict, given: dict) -> tuple[float, bool]` → `(fraction, is_full)`:
  - `mcq`/`tf`/`image`: `1.0/True` if `given["index"] == data["correct_index"]`, else `0.0/False`.
  - `match`: `fraction = correct_pairs / total_pairs` from `given["pairs"]` vs `data["correct_pairs"]`; `is_full = fraction == 1.0`.
  - `order`: `fraction = correctly_placed / n` from `given["sequence"]` vs `data["correct_sequence"]`; `is_full`.
- `score_answer` extended to accept a `fraction`:
  `points = round((base_points + speed_bonus(time_ms)) * fraction * streak_multiplier(streak_before))`.
  (Existing boolean callers map to `fraction ∈ {0.0, 1.0}`.)

`submit` uses `grade` per answer; **streak and accuracy advance only when `is_full`**; it accumulates `max_streak` and persists it on the attempt.

## 6. Badges — new `app/badges.py`

- `evaluate(summary: dict) -> list[str]` where `summary` has
  `accuracy, max_streak, avg_speed_bonus, is_first_finish`:
  - `perfect_quiz` if `accuracy == 1.0`
  - `streak_master` if `max_streak >= 5`
  - `speed_demon` if `avg_speed_bonus >= 35` (of max 50)
  - `first_finish` if `is_first_finish`
- `award(conn, contestant_id, codes) -> list[str]` — inserts with
  `INSERT OR IGNORE`; returns the codes that were **newly** earned.
- `get_badges(conn, contestant_id) -> list[str]`.
- `top_badge(conn, contestant_id) -> str | None` — highest-priority earned badge
  for leaderboard icons (priority: perfect > streak > speed > first).

Wired into `submit`: after finishing, build `summary`, `award`, and include both
`earned_now` and `all_badges` in the report dict.

## 7. Auto-DM — new `app/notify.py`

- `send_report_dm(user_id: int, text: str) -> bool` — POSTs to
  `https://api.telegram.org/bot<token>/sendMessage` via `httpx` (already a dep),
  3 s timeout. Returns success; **never raises** (logs and returns False on
  error). `submit` calls it after persisting, passing
  `report.format_report_text(...)` plus a badges line. A failed DM does not
  affect the API response. Disabled automatically when `BOT_TOKEN` is empty
  (tests set it empty or monkeypatch the function).

## 8. Overall leaderboard

- `models.leaderboard_overall(conn, limit=20)` → per contestant, sum of
  `MAX(total_score)` grouped by quiz, ordered desc; columns
  `first_name, total_score`.
- `GET /api/leaderboard?scope=overall` returns it; `scope=quiz&slug=` (default)
  is unchanged. Each leaderboard row also carries `top_badge` for icons.

## 9. Frontend (`frontend/app.js`, `index.html`, `styles.css`)

- **Runner** — new renderers:
  - `match`: two columns (left fixed slots, right draggable cards). Pointer-event
    drag drops a right card onto a left slot; tapping a placed card returns it.
    Answer = `{pairs: [[li, ri], ...]}`.
  - `order`: a vertical list of draggable rows reordered by pointer drag.
    Answer = `{sequence: [original_index, ...]}`.
  - A shared tiny pointer-drag helper (`pointerDrag`) used by both; no library.
- **Report** — a "badges earned" row that pops newly-earned badges.
- **My Badges screen** (`screen-badges`) — grid of all 4 badges, locked/unlocked
  from `GET /api/me/badges`; reachable from a home button.
- **Leaderboard rows** — render the `top_badge` icon next to the name; a toggle
  for per-quiz vs overall.

## 10. Content

Add ~2 real match/order questions to `content/questions/journals.json`:
- **order**: rank real journal-selection filters by importance (real
  database-filter screenshot as the asset).
- **match**: match real predatory red-flag snippets to their scam-tactic names.
Sourced from genuine public material and anonymized, with `source_url`
provenance, exactly like Phase 1. `content_schema` validates the new shapes.

## 11. Validation — `app/content_schema.py`

Extend `validate_quiz` to accept `match` and `order`:
- `match`: non-empty `left_ar`, `right_ar`, and `correct_pairs` whose indices are
  in range; each left maps to exactly one right.
- `order`: `items_ar` non-empty and `correct_sequence` a permutation of
  `range(len(items_ar))`.

## 12. API surface (delta)

- `POST /api/quizzes/{slug}/submit` — now grades match/order, persists
  `max_streak`, awards badges, fires the DM, and returns `earned_now` +
  `all_badges` in the report.
- `GET /api/leaderboard?scope=overall|quiz&slug=` — adds overall; rows include `top_badge`.
- `GET /api/me/badges` — authenticated via `initData`; returns the caller's earned badge codes.

## 13. Testing

- **scoring:** `grade` for match (partial, full, none, malformed), order
  (partial, exact, reversed), and mcq/tf/image; `score_answer` with fractions.
- **badges:** `evaluate` for each badge boundary; `award` idempotency; `top_badge` priority.
- **content_schema:** valid + invalid match/order docs.
- **api:** a match/order submit that scores partially and awards `first_finish`;
  `scope=overall` aggregation; `/api/me/badges` auth (401 on bad initData).
- **notify:** monkeypatched/stubbed — assert `submit` still succeeds when the DM
  fails, and that it is invoked with the right user id.
- **migration:** `migrate` is idempotent and preserves existing
  `questions`/`answers` rows + ids.

## 14. Out of scope

- **Phase 2B:** the other 3 quizzes (foundations, paper types, paper parts) with
  real artifacts.
- **Phase 3:** live timed sessions, WebSocket upgrade.
- No change to auth, hosting, or the Cloudflare tunnel deploy.
