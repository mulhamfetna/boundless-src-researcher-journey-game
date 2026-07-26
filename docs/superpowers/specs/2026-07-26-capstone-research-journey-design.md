# Design Spec — Capstone "Research Journey" (رحلة البحث الكبرى)

**Date:** 2026-07-26
**Status:** Draft for review
**Depends on:** the application-first engine (spot/mcq/tf/image/match/order, retry/hint, client-side checking), the journals pilot (`spot`).

## 1. Purpose

A **flagship end-to-end mode**: instead of per-topic stations, one continuous research **project** the player carries up the Arcane climb (Zaun → Piltover summit), where research skills **compound**. The player *does a whole paper* — spot the gap → design the method → assemble IMRaD → choose the journal (dodge a predatory trap) → pass ethics → survive Reviewer 2 → earn the **Senior Researcher** badge.

**The unified project (narrative spine):** "أثر التعرض التراكمي لجسيمات الهكستيك على الوظائف التنفسية والإدراكية لدى عمال مناجم زاون" — a realistic occupational-epidemiology study; every task references this same ongoing project so continuity is *felt*.

## 2. Scope (v1 — MVP)

- **Linear narrative journey**, not choice-branching. The same project threads all 6 stages via the prompts; progression is **performance-based** (retry/hint/badge). Stage N does not literally consume stage N-1's chosen answer — that (true branching/state threading) is **deferred to v2**.
- **Reuses the whole engine** — no new interaction types. The capstone is a **content quiz** (`slug: capstone`) played **in authored order** (no sampling), plus a completion **badge**, plus its **auto map node**.

## 3. Architecture (three small touches + content)

1. **Ordered playback (engine):** `GET /questions` samples/shuffles via `sample_questions`. The capstone must play its 12 tasks **in authored stage order**. Gate it: in `api.py`, `if quiz["slug"] in ORDERED_SLUGS: served = out (authored order) else: sample`. `ORDERED_SLUGS = {"capstone"}`. `get_questions` already returns `ORDER BY display_order, id`, so authored order is preserved. No migration.
2. **Completion badge (engine):** add `senior_researcher` to `badges.ALL_CODES` + a sprite; award it when a **capstone** attempt is finished (completing the journey, regardless of score). Surfaced like other badges (report, board, "أوسمتي", DM). Wire in the submit/award path (pass the quiz slug to the badge computation).
3. **Auto map node (frontend):** the map lists quizzes from `/api/quizzes`, so `capstone` appears automatically. Give it a distinct title («رحلة البحث الكبرى») and a `STAGE_SPRITES.capstone` icon; place it last (`display_order` high) as the summit. The existing runner renders every task type already.

**Content:** `content/questions/capstone.json` — the 12 curated tasks below, in order, `slug:"capstone"`, `display_order: 99`, with `fun_facts_ar`.

## 4. The 12 tasks (curated from agy; research-accurate)

Concepts map to **existing slugs** so the journey feeds overall mastery.

| Stage | id | type | concept | task |
|---|----|------|---------|------|
| S1 Zaun | `cap-s1-gap` | mcq | research_gap | from 3 prior abstracts, pick the true unstudied gap |
| S1 Zaun | `cap-s1-question` | mcq | research_gap | pick the precise FINER research question |
| S2 Lab | `cap-s2-variables` | match | methodology_basics | classify exposure/outcome/control/instrument |
| S2 Lab | `cap-s2-design` | mcq | methodology_basics | choose prospective cohort (can't ethically RCT a harm) |
| S3 Workshop | `cap-s3-imrad` | order | structure | order Intro→Methods→Results→Discussion |
| S3 Workshop | `cap-s3-sections` | match | structure | map each draft paragraph → its IMRaD section |
| S4 Library | `cap-s4-predatory` | spot | predatory_signs | flag the predatory red-flags among 4 invites |
| S4 Library | `cap-s4-journal` | mcq | journal_selection | pick the Q1, in-scope, indexed venue |
| S5 Gate | `cap-s5-ethics` | spot | ethics | flag the Helsinki violations (coercion, bad consent, no care) |
| S5 Gate | `cap-s5-cover` | mcq | submission | the cover letter's key element (novelty + no COI + no dual submit) |
| S6 Summit | `cap-s6-reviewer2` | mcq | peer_review | the professional evidence-backed rebuttal (ANCOVA + power analysis) |
| S6 Summit | `cap-s6-final` | tf | peer_review | resubmit w/ point-by-point + track changes → acceptance |

Full player-facing Arabic text, options, correct answers, and explanations are authored in `capstone.json` from the curated draft (`/tmp/agy_trial/capstone.md`), with these fixes: task S1.1 is `mcq` (single correct, not `spot`); the `order` task uses items in correct order with `correct_sequence [0,1,2,3]`; every task carries a `concept` from the table.

The journey ends on the report with a crowning line and the **Senior Researcher** badge.

## 5. Testing

- **Backend:** `capstone.json` validates; `GET /api/quizzes/capstone/questions` returns **all 12 in authored order** (not sampled/shuffled); recall stations still sample (regression); `senior_researcher` is awarded on a finished capstone attempt and appears in `get_badges`.
- **Frontend:** existing runner/spot tests stay green (the capstone reuses them). Add a small test that `STAGE_SPRITES.capstone` resolves + the badge code is known.
- **Manual/Playwright:** enter «رحلة البحث الكبرى» from the map, verify the 12 tasks play in order and the badge shows on the report.

## 6. Out of scope (v2)

- True choice-branching / state threading (stage N consumes stage N-1's output).
- A bespoke journey UI (stage banners, a distinct climb screen) beyond the reused runner + narrative prompts + distinct node.
- Free-form authoring (question/cover-letter writing) with rubric self-check.
