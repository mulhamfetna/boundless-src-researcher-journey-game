# Design Spec — Applied Question Bank (real-paper, hands-on)

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phase 3B sampling + the four concept-tagged quizzes

## 1. Purpose

Shift the quizzes from theory recall toward **hands-on, applied** questions built on **real
open-access papers**, per `questions-samples.md`. The learner reads a real paper excerpt (or a real
screenshot) and **identifies / judges / chooses** — the hint pushes them to *do the thing* (count
words, check the journal rank, read the paragraph), never "what is the definition of X".

Rollout is a **pilot first** (one quiz: `paper-parts`), validated live, then scaled to the others.

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Artifact form | **Both** — a real **text-excerpt block** (backbone) + real **screenshots** where the thing is visual (reference list, ranking/Scimago table). |
| Sourcing | **I fetch + curate from DOAJ** (open-access). Each question records a `source_url`. |
| Rollout | **Pilot ~8–10 applied questions on `paper-parts`**, ship, react, then scale to journals/foundations/paper-types. |
| Style | Applied "identify/judge/choose from real material"; hints make the learner act; theory questions stay but the applied ratio rises. |

## 3. Question format (additive schema change)

Reuse the existing `mcq`/`image` types; add two **optional** fields to a question:

- **`passage`** — the real excerpt text (English, as papers are). Rendered LTR in a styled "paper"
  block above the prompt + options.
- **`source_url`** — provenance (the DOAJ article / journal). Shown as a small "المصدر" link and in
  the report review.

`asset` (existing) remains for true **screenshots**. All other fields unchanged: `prompt_ar`,
`options_ar`, `correct_index`, `explanation_ar`, `concept`, `hint_ar`, `base_points`.

A question may carry `passage` and/or `asset`. `concept` stays **required** (Phase 3B). Validation:
`passage`/`source_url`, when present, are non-empty strings.

## 4. Sourcing pipeline

- **`scripts/fetch_papers.py`** — query the DOAJ API (`https://doaj.org/api/search/articles/...`)
  for open-access, English, abstract-bearing articles; write candidates to
  `content/papers/<topic>.json`: `{title, journal, authors, abstract, source_url, license}`
  (and full-text URL when present). Read-only research aid; never auto-writes questions.
- **Curation (me):** select excerpts, write the Arabic `prompt_ar`/`options_ar`/`explanation_ar`,
  tag `concept`, set `passage` + `source_url`, add to the quiz JSON. For "visual" questions, fetch
  the OA PDF and render the cited page with `pdftoppm` to `content/assets/<quiz>/`, recording the
  `source_url`.
- **Provenance / licensing:** DOAJ articles are open-access (mostly CC). We use **short excerpts +
  a citation** (`source_url`, journal) — educational fair use. Store `source_url` on every
  real-paper question.

## 5. Wiring (backend + frontend)

- **`content_schema.py`:** accept optional `passage`/`source_url` (non-empty strings) on
  `mcq`/`image` questions.
- **`seed.py`:** persist `passage`/`source_url` into `data_json` (like `hint_ar`).
- **`api.py` `get_questions`:** include `passage`/`source_url` in the serialized question.
- **`report.py` `build_report`:** carry `passage`/`source_url` into the per-item review.
- **Frontend runner (`app.js`/`styles.css`):** if `q.passage`, render a scrollable **LTR**
  `.passage` paper-block (arcade-styled, monospace-ish) above the options; render a small
  `المصدر` link when `source_url` is present. Report review shows the same.

## 6. Pilot scope (`paper-parts`)

Add **~8–10 applied `mcq` questions** to `content/questions/paper-parts.json`, each built from a real
DOAJ paper, e.g.:
- *[real abstract]* → "ما هذا القسم؟" (`concept: abstract`), hint: "ابحث عن جملة الهدف + الخلاصة".
- *[real methods paragraph]* → "ما هذا القسم؟" (`concept: methods`).
- *[paragraph with an injected flaw]* → "ما الخلل في هذه الفقرة؟" (`concept: structure`).
- *[four short excerpts]* → "أيّها الملخص؟" (`concept: abstract`).

Each carries `passage` + `source_url` + `concept` + `hint_ar` + `explanation_ar`. They join the
existing bank and flow through Phase 3B sampling and the runner unchanged.

## 7. Out of scope (this spec / future)

- Scaling to journals/foundations/paper-types (after the pilot validates the format).
- A new question *type* (the optional `passage`/`asset` on `mcq` is enough).
- Auto-generating questions from papers (curation stays human).
- `content/papers/` raw candidates are a dev aid (gitignored like `content/raw/`).

## 8. Testing

- **Schema:** a question with `passage`+`source_url` validates; an empty-string `passage` fails;
  questions without them still validate.
- **Seed/API:** `passage`/`source_url` round-trip through `seed_quiz` → `get_questions`.
- **Report:** `build_report` includes `passage`/`source_url` on items that have them.
- **Frontend:** the runner renders a `.passage` block + `المصدر` link when a question has them
  (Vitest); existing runner/drag tests stay green.
- **`fetch_papers.py`:** a smoke test that it parses a DOAJ API response into candidate dicts
  (mock the HTTP body; no live call in the test).
- **Seed-integrity:** every question still has a `concept`; pilot adds keep `paper-parts` ≥ 25.

## 9. Deployment

Content + small schema/serialization change → after deploy **re-seed** `paper-parts`
(`seed_all`); no DB migration (fields live in `data_json`). Frontend cache-busts automatically.
Re-seeding resets that quiz's attempts (accepted).
