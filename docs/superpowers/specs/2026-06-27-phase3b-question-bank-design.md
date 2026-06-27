# Design Spec — Phase 3B: Applied Question Bank + Per-Attempt Sampling

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com
**Builds on:** Phases 1, 2A, 2B, 3A (live at src.mulhamfetna.com)

## 1. Purpose

Make each quiz feel fresh on replay. Today every attempt serves the *entire* fixed
bank (12–15 questions) in the same order. Phase 3B:

1. Grows each quiz's bank with **applied/synthetic** questions (illustrative where
   synthetic, per the standing rule), tagged by **concept**.
2. Serves a **random, concept-balanced sample of ~10** questions per attempt, so a
   returning contestant rarely sees the same set twice (**statistical** never-repeat —
   no per-user tracking).

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Never-repeat semantics | **Statistical**: large bank + random per-attempt sampling. No per-contestant "seen" tracking; `GET /questions` stays unauthenticated and stateless. |
| Sample size | **10 per attempt**, constant, overridable via env `SAMPLE_SIZE`. If a bank has < `SAMPLE_SIZE` questions, return all of them. |
| Sampling shape | **Balanced (stratified) across `concept`** — spread the 10 evenly over the quiz's concepts, not clustered on one. |
| Sampling location | **Server-side**, inside `GET /questions`. |
| Bank size | **Grow incrementally** — reach ~30/quiz now, structured so appending more later is trivial. |
| Authoring | **I draft, auto-accept** — generate applied/scenario questions tagged by concept; seed without a manual gate; user spot-checks live. |
| Accuracy denominator | **Fix**: accuracy = first-try count ÷ **questions answered in the submission**, not ÷ full bank. |

## 3. Architecture

```
content/questions/<slug>.json   ← bigger bank; every question has "concept"
        │ seed_all + migrate (unchanged loaders)
        ▼
   SQLite questions (data_json now carries concept)
        │
GET /api/quizzes/{slug}/questions
        │  load full bank → app.sampling.sample_questions(bank, SAMPLE_SIZE, rng)
        ▼  returns ONLY the sampled ~10 (with answer keys, as today)
   Mini App runner (unchanged — renders whatever it's handed)
        │  submit {question_id, retries, hint_used}
        ▼
POST /api/quizzes/{slug}/submit
   scores by question_id lookup (already works for any subset);
   accuracy denominator = len(answers in payload)
```

Design keeps Phase 3A's client-side checking intact: the sampled questions still ship
with `correct_index` / keys / explanations / hints.

## 4. Components

### 4.1 Schema — `concept` (in `app/content_schema.py`)
- Every question requires a non-empty string `concept`.
- `validate_quiz` raises `SchemaError` if any question lacks `concept`.
- No other schema change. `concept` is stored inside `data_json` (no DB migration:
  `data_json` is already free-form JSON), surfaced by the seed/serialization path the
  same way `hint_ar` is.

### 4.2 Sampling engine — new `app/sampling.py`
- `sample_questions(questions: list, size: int, rng) -> list`
  - Group `questions` by their `concept`.
  - Round-robin across concept groups (each group internally shuffled by `rng`),
    taking one at a time until `size` is reached or all exhausted → even concept spread.
  - If `len(questions) <= size`, return all (shuffled by `rng`).
  - Deterministic given a seeded `rng` (e.g. `random.Random(seed)`), for testability.
- Pure function. No DB, no global state. `rng` is injected.
- `SAMPLE_SIZE` default `10`, read from env in `app/config.py` (`Settings.sample_size`).

### 4.3 `GET /questions` wiring (in `app/api.py`)
- Build the full serialized question list as today.
- `sampled = sample_questions(full, settings.sample_size, random.Random())`.
- Return `sampled` in place of `out`. `fun_facts_ar` unchanged (quiz-level).
- Each serialized question must include its `concept` (from `data_json`) so the sampler
  can stratify. `concept` may also be returned to the client (harmless; UI ignores it).

### 4.4 `submit` accuracy fix (in `app/api.py`)
- Replace `total_questions = len(qrows)` (full bank) with
  `total_questions = len(answers)` (the submitted/sampled set), guarding divide-by-zero.
- `first_try_count` and streak logic unchanged. Badges unchanged.
- Rationale: a 10-question attempt scoring 9 first-try is 90% accuracy, not 9÷51.

### 4.5 Content expansion (`content/questions/*.json`)
- Backfill `concept` on the existing 51 questions (group them under the natural concepts
  of each PDF).
- Author applied/scenario synthetic questions (illustrative) to bring each quiz to ~30,
  each tagged by `concept`, reusing Phase 3A fields (`option_explanations_ar`, `hint_ar`).
- Concepts per quiz are derived from each PDF's teaching points (e.g. journals:
  `predatory_signs`, `indexing`, `quartiles`, `metrics`, `open_access`, `peer_review`).
- Deploy path unchanged: rebuild → `python -m app.migrate` → `seed_all` → up.

## 5. Out of scope (YAGNI / future)
- Per-contestant "seen" tracking / strict never-repeat (explicitly rejected — statistical).
- Per-quiz configurable sample size (fixed 10 + env override is enough).
- Difficulty tiers / adaptive difficulty (concept tag only for now).
- Authenticating `GET /questions` (stays open; client-side checking already accepts that
  scores are not tamper-proof — a Phase 3A tradeoff).

## 6. Testing
- **`sample_questions`** (seeded RNG): returns exactly `size` when bank > size; balances
  across concepts (no concept over-represented when counts allow); returns all when
  bank ≤ size; deterministic for a fixed seed; handles a single-concept bank.
- **Schema**: a question missing `concept` fails `validate_quiz`; a valid tagged doc passes.
- **`submit` accuracy**: a 3-answer submission with 2 first-try → accuracy ≈ 0.667
  (denominator = 3, not full bank).
- **Seed integrity**: every seeded question has a non-empty `concept`.
- **`GET /questions`**: returns ≤ `SAMPLE_SIZE` questions; all returned ids belong to the
  quiz; still includes answer keys + hints.

## 7. Decomposition
One implementation plan, ordered: (1) schema `concept` + config `SAMPLE_SIZE`,
(2) `sampling.py` engine (TDD), (3) wire into `GET`, (4) accuracy fix, (5) backfill
concepts on existing 51 + integrity test, (6) author applied questions to ~30/quiz.
Steps 1–5 are the engine (small, high-confidence); step 6 is bulk content that can grow
incrementally afterward.
