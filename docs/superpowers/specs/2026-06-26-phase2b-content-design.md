# Design Spec — Phase 2B: Remaining Quizzes

**Date:** 2026-06-26
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phase 1 + Phase 2A (live at `https://src.mulhamfetna.com`). Engine
(question types mcq/tf/image/match/order, partial credit, badges, per-quiz +
overall leaderboards, auto-DM) is complete and unchanged by this phase.

## 1. Purpose

Turn the three remaining research-methodology PDFs into three new playable
quizzes, so the app covers all four sessions. This phase is ~90% content
authoring plus small multi-quiz plumbing; it adds NO new mechanics.

## 2. Confirmed decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Scope | All 3 remaining PDFs, as separate quizzes, in one pass |
| Per-quiz size | ~10–13 questions, mix of mcq/tf/match/order, **≥1 match and ≥1 order each** |
| Image artifacts | **Retry web sourcing**; genuine public artifacts where possible, **text-only fallback** where blocked. Never fabricate a source_url. |
| Authoring | I draft from the PDFs; user curates before go-live |
| Language | Arabic, RTL |

## 3. New quizzes

| slug | PDF filename | covers | display_order |
|------|--------------|--------|---------------|
| `foundations` | `أسس البحث العلمي واختيار الفجوة البحثية.pdf` | foundations of scientific research; choosing the research gap | 2 |
| `paper-types` | `أنواع الأوراق البحثية العلمية.pdf` | types of scientific research papers | 3 |
| `paper-parts` | `اجزاء الورقة البحثية.pdf` | parts of a research paper | 4 |

(The existing `journals` quiz keeps `display_order` 1.) Each quiz is a curated
`content/questions/<slug>.json` validated by the existing
`app.content_schema.validate_quiz`, with assets (if any) under
`content/assets/<slug>/` carrying real `source_url` provenance.

## 4. Content pipeline (per quiz)

1. `scripts/extract.py "<pdf>" content/raw/<slug>.txt` → distill the real
   teaching points.
2. Author `content/questions/<slug>.json` grounded in that text: ~10–13
   questions, mixing mcq/tf/match/order, ≥1 match + ≥1 order. Add an `image`
   question only when a **genuine public artifact** is sourced (retry web; if
   blocked, that question becomes text or is dropped — no fabricated assets).
3. Validate with `validate_quiz`.

## 5. Engine changes (small)

- **`app.seed.seed_all(conn, dir="content/questions") -> list[str]`** — seed
  every `*.json` in the directory (each via the existing idempotent `seed_quiz`),
  returning the slugs seeded. Deploy uses this to load all quizzes in one step.
- **Bot `/leaderboard`** currently hardcodes `slug="journals"`. With four
  quizzes, switch it to the **overall** board: a new pure helper
  `app.bot.overall_leaderboard_text(conn) -> str` built on the existing
  `models.leaderboard_overall`. The Mini App already supports the quiz/overall
  toggle and lists all quizzes on home — no frontend change.

## 6. Data flow

No schema change. New quizzes are rows in the existing `quizzes`/`questions`/
`assets` tables. The overall leaderboard (`SUM` of best-per-quiz) becomes
meaningful across four quizzes. Per-quiz boards work unchanged.

## 7. Testing

- **TDD:** `seed_all` (seeds N quiz files; idempotent on re-run; returns slugs);
  `overall_leaderboard_text` (lists names + summed scores; empty-state message).
- Content validated by `validate_quiz` for every new file.
- Manual: all four quizzes appear on home and are playable; match/order render;
  overall board ranks across quizzes; bot `/leaderboard` shows the overall board.

## 8. Deploy

Rebuild images, run `app.migrate` (idempotent — no schema change, returns
"already current"), seed all quizzes via `seed_all`, restart, verify
`/api/quizzes` lists all four and `?scope=overall` spans them. Re-seeding resets
play data per the documented behavior (acceptable pre-launch).

## 9. Out of scope

- Phase 3: live timed sessions, WebSocket upgrade.
- A combined "final boss" quiz across all PDFs (deferred).
- Any change to scoring, auth, badges, or the Mini App runner/report.
