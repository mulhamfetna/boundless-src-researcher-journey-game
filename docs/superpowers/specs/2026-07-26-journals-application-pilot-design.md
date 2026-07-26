# Design Spec — Journals Station: Application-First Pilot ("do the researcher's job")

**Date:** 2026-07-26
**Status:** Draft for review
**Owner:** xnokia@gmail.com
**Depends on:** existing Mini App engine (mcq/tf/image/match/order + retry/hint/explanations/concept tags, client-side checking), the real journals artifacts already shipped (`content/assets/journals/{predatory_email,journal_quartile,journal_finder}.png/jpg`).

## 1. Purpose & intent

Turn the **journals** station from a *recall* quiz (30 questions like "which database issues the JIF?") into **hands-on application**: the player evaluates real artifacts (a predatory solicitation email, a Scimago quartile badge, a JANE results screen, journal metric cards) and **makes and defends a researcher's decision** — submit or walk away, which venue, which metric, which OA model.

This is the **pilot** that proves the application-first model on the live app and builds the one reusable new interaction (`spot`). Once proven, the same pattern + interaction feed the Capstone "Research Journey" and the other five stations (out of scope here).

**Non-goal:** memorization. Every task is framed *artifact → decision*, never *definition → recall*.

## 2. The one new interaction: `spot` (red-flag multi-select)

The only engine addition. Everything else reuses existing types.

- **What the player does:** an artifact is shown (image or text card) with a set of **tappable chips**; the player selects **all** the correct items (e.g., the red flags) and hits **تحقّق** (check).
- **Skill built:** critical appraisal — spotting *which* signals matter, from a realistic mixed set (real red flags + deceptive-but-legit-looking distractors).
- **Correctness:** the selected set must **equal** the target set exactly (all red flags found, no false positives).
- **Fits the Khan-style engine unchanged:** retry-until-correct — a wrong check counts as a retry (highlighting over-/under-selected chips), the player adjusts and re-checks; `hint` reveals how many remain or surfaces one flag; scoring is the existing retry/hint-aware formula (no new scoring math — spot correctness is just set-equality decided client-side, then `{question_id, retries, hint_used}` is submitted like every other type).

**Schema (`content_schema.py`, add `"spot"` to `VALID_TYPES`):**
```json
{
  "type": "spot",
  "prompt_ar": "…",
  "concept": "predatory_signs",
  "base_points": 120,
  "options_ar": ["chip A", "chip B", "chip C", "chip D", "chip E", "chip F"],
  "correct_indices": [0, 1, 3],
  "chip_explanations_ar": ["why A is a flag", "…", …],
  "explanation_ar": "overall takeaway",
  "asset": { "file": "assets/journals/predatory_email.png", "source_url": "…" }
}
```
**Validation rules:** `options_ar` a list ≥ 3; `correct_indices` a non-empty list of in-range ints; **at least one non-correct chip** (a distractor); `asset` optional (text-card tasks have none).

**Frontend touchpoints (vanilla JS, ~40–60 lines):**
- `GET /questions` exposes `options_ar` + `correct_indices` (client-side checking — consistent with the existing accepted tradeoff that scores aren't tamper-proof).
- Runner renders chips as toggle buttons + a check button; on check compares `Set(selected) === Set(correct)`; wrong → mark extra selections red, missed ones (on give-up/hint) amber; retry.
- Seed stores `{options_ar, correct_indices, chip_explanations_ar}` in `data_json` (same pattern as match/order).

## 3. The pilot content — 7 journals application tasks

(Concepts already in use: `predatory_signs, indexing, quartiles, metrics, open_access, journal_selection`. Player-facing text is Arabic; light Arcane flavor, **real** methodology.)

| # | id | type | concept | skill |
|---|----|------|---------|-------|
| 1 | `predatory-email-spotter` | **spot** | predatory_signs | appraise a real solicitation, flag the predatory signals |
| 2 | `quartile-venue-decision` | image | quartiles | read a Scimago Q3 badge → judge venue fit |
| 3 | `jane-finder-selection` | mcq | journal_selection | interpret JANE results → pick best-fit venue |
| 4 | `fake-index-audit` | tf | indexing | tell a fake metric ("Global Impact Factor") from a real one |
| 5 | `oa-models-matching` | match | open_access | match publishing scenario → OA model (Green/Gold/Diamond/Hybrid) |
| 6 | `researcher-metric-choice` | mcq | metrics | pick the right metric for a purpose (individual → h-index) |
| 7 | `journal-vetting-sequence` | order | journal_selection | order the vet-before-submit steps |

**Task 1 — `predatory-email-spotter` (spot, artifact `predatory_email.png`)**
Prompt: «وصلتك هذه الدعوة للنشر في بريد معملك. حدِّد **كل** العلامات الحمراء التي تدل أنها مجلة مفترسة قبل أن ترسل بحثك.»
Chips (aligned to what the real image shows):
- ✅ «وعد بنشر سريع مضمون (40–90 يومًا)» — guaranteed speed = fee-farming, not real review.
- ✅ «دعوة فورية للانضمام لهيئة التحرير/التحكيم» — unsolicited board invites are a classic tell.
- ✅ «خصم على رسوم النشر عند الدفع الفوري» — commercial urgency.
- ✅ «إطراء مبالغ على "بحثك"» — mass-personalized flattery.
- ❌ «وجود رقم ISSN» — predators have ISSNs too; presence ≠ legitimacy (distractor).
- ❌ «ذكر أنها "محكّمة" (Peer-reviewing)» — *claiming* review isn't proof; verify indexing (distractor).
Takeaway: predators **display** legitimacy signals (ISSN, "peer-reviewed", OA) to deceive; the red flags are the unrealistic guarantees + solicitation + fee pressure.

**Task 2 — `quartile-venue-decision` (image `journal_quartile.png`, SJR value taken from the real badge).**
«قرأت هذه الشارة للمجلة المرشّحة. ما القرار الأصح أكاديميًا؟» → ✅ «Q3 يعني الربع الثالث (50–75%) في تخصصها؛ مناسبة لدراسة مسحية محدّدة، لا لاكتشاف كبير يستهدف Q1.» Distractors: "Q1 because SJR>0.4" (wrong — Q = field rank not raw SJR), "unranked" (wrong), "forces APC" (wrong — quartile ≠ funding model).

**Task 3 — `jane-finder-selection` (mcq, image `journal_finder.jpg`).**
✅ highest Confidence/scope-match **and** Open Access. Distractors: highest IF regardless of scope (→ desk-reject), first-in-list even if unindexed, longest-abstract/closed.

**Task 4 — `fake-index-audit` (tf, text card).**
Card: a journal boasting "Global Impact Factor (GIF) 4.8", "Scientific Indexing Service". Q: is this an official rigor indicator? → ✅ **خطأ.** GIF / Universal Impact Factor are fabricated predatory metrics; the real JIF is Clarivate/Web of Science only.

**Task 5 — `oa-models-matching` (match, text card).** Green OA = self-archiving in a repo; Gold OA = author pays APC, free on site; Diamond OA = free for author & reader (institutionally funded); Hybrid = subscription journal with optional per-article APC.

**Task 6 — `researcher-metric-choice` (mcq, text card).** Measure an *individual* researcher's cumulative output+impact → ✅ **h-index**; JIF/CiteScore/SJR are journal-level (distractors, each with why).

**Task 7 — `journal-vetting-sequence` (order, text card).** scope + finder (JANE) → verify indexing (Scopus/WoS) + board → Think.Check.Submit / blacklist check → author guidelines + APC → submit via official portal.

## 4. Integration & deploy

- **Journals becomes application-first.** Replace the 30 recall questions in `content/questions/journals.json` with these 7 application tasks (expandable later). With `SAMPLE_SIZE=10` and a 7-task bank, sampling returns **all 7** every attempt (bank ≤ size), so the whole applied set is always played.
- **Re-seed required** → journals leaderboard resets (accepted; note it).
- Other five stations keep their recall content **unchanged** in this pilot.
- Deploy: content + one frontend interaction + schema. `docker compose up -d --build web` → re-seed journals. No DB migration (spot lives in `data_json`).

## 5. Testing

- **Backend (pytest):** `content_schema` accepts a valid `spot`, rejects (empty `correct_indices`, out-of-range index, no distractor, <3 chips); seed round-trips a `spot` (options + correct_indices in `data_json`); the curated `journals.json` validates.
- **Frontend (vitest):** `spot` renders chips + check button; set-equality check (exact match solves; extra/missing = wrong→retry); hint path.
- **Manual:** play journals in Telegram — each task reads as a *decision*, retry/hint/explanations work, artifacts render.

## 6. Out of scope (next, once this is proven)

- The **Capstone "Research Journey"** (end-to-end, cross-stage state) — reuses `spot` + this authoring pattern.
- Converting the other five stations to application-first.
- Free-form tasks needing real evaluation (guided slot-builder + rubric self-check) — deferred; not needed for these 7.
- Any server-side answer verification (client-side checking stays the accepted model).
