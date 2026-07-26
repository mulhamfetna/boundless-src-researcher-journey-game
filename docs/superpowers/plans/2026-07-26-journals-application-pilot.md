# Journals Application Pilot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Turn the journals station from recall into hands-on application — add one new `spot` interaction (red-flag multi-select) and replace the 30 recall questions with 7 curated application tasks.

**Architecture:** `spot` is a client-side-checked multi-select: the artifact + tappable chips render in the runner; correctness is exact set-equality of selected vs. `correct_indices`; it reuses the existing retry/hint/scoring model unchanged (submit stays `{question_id, retries, hint_used}`). Backend only validates the new type and stores/exposes its data in `data_json` (same pattern as match/order). No DB migration.

**Tech Stack:** Python 3 + stdlib sqlite3 + FastAPI (backend), vanilla JS + Vitest/jsdom (frontend). Spec: `docs/superpowers/specs/2026-07-26-journals-application-pilot-design.md`.

## Global Constraints

- **Client-side checking stays** — `GET /questions` exposes answer keys (accepted tradeoff); scoring is retry/hint-based, not answer-verifying. No server-side spot verification.
- **Frontend-only for the interaction; content-only for tasks 2–7.** Dependency-free vanilla JS. RTL Arabic. Preserve element IDs; `typeof`-guard cross-module calls.
- **Cache-busting is automatic** (`main.py` stamps `?v=`); never hand-edit versions.
- **Every question needs a non-empty `concept`.** Concepts in use: `predatory_signs, indexing, quartiles, metrics, open_access, journal_selection`.
- **Re-seeding wipes attempts** → journals leaderboard resets on deploy.
- Commit after every task.

---

### Task 1: `spot` schema validation

**Files:**
- Modify: `backend/app/content_schema.py`
- Test: `backend/tests/test_content_schema.py`

**Interfaces:**
- Produces: `validate_quiz` accepts `type:"spot"` with `options_ar` (list ≥3), `correct_indices` (non-empty list of in-range ints), at least one non-correct chip; `asset` optional. Rejects otherwise.

- [ ] **Step 1: Write failing tests** (append to `test_content_schema.py`)

```python
def _spot_q():
    return {"type": "spot", "prompt_ar": "حدد العلامات الحمراء", "concept": "predatory_signs",
            "options_ar": ["أ", "ب", "ج", "د"], "correct_indices": [0, 2]}

def test_valid_spot_passes():
    doc = _good_doc(); doc["questions"].append(_spot_q()); validate_quiz(doc)

def test_spot_empty_correct_indices_fails():
    doc = _good_doc(); q = _spot_q(); q["correct_indices"] = []; doc["questions"].append(q)
    with pytest.raises(SchemaError): validate_quiz(doc)

def test_spot_index_out_of_range_fails():
    doc = _good_doc(); q = _spot_q(); q["correct_indices"] = [0, 9]; doc["questions"].append(q)
    with pytest.raises(SchemaError): validate_quiz(doc)

def test_spot_needs_a_distractor():
    doc = _good_doc(); q = _spot_q(); q["correct_indices"] = [0, 1, 2, 3]; doc["questions"].append(q)
    with pytest.raises(SchemaError): validate_quiz(doc)

def test_spot_min_three_chips():
    doc = _good_doc(); q = _spot_q(); q["options_ar"] = ["أ", "ب"]; q["correct_indices"] = [0]
    doc["questions"].append(q)
    with pytest.raises(SchemaError): validate_quiz(doc)
```

- [ ] **Step 2: Run, expect FAIL** — `cd backend && pytest tests/test_content_schema.py -q`

- [ ] **Step 3: Implement.** Add `"spot"` to `VALID_TYPES`. In the per-question loop, add a branch (mirror the match/order branches):

```python
elif q["type"] == "spot":
    opts = q.get("options_ar")
    _require(isinstance(opts, list) and len(opts) >= 3, f"{where}: spot needs >= 3 chips")
    ci = q.get("correct_indices")
    _require(isinstance(ci, list) and ci, f"{where}: spot needs non-empty correct_indices")
    _require(all(isinstance(i, int) and 0 <= i < len(opts) for i in ci),
             f"{where}: spot correct_indices out of range")
    _require(len(set(ci)) < len(opts), f"{where}: spot needs at least one non-correct chip")
```

Ensure the earlier option-type branch (`if q["type"] in ("mcq","tf","image")`) is not entered for `spot` (spot is handled in its own `elif`, so it skips the `options_ar`/`correct_index` block — confirm the branch structure).

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(schema): validate spot (red-flag multi-select) question type"`

---

### Task 2: seed + question serialization for `spot`

**Files:**
- Modify: `backend/app/seed.py` (store spot data in `data_json`), and the `GET /questions` serializer (find it: `grep -rn "options_ar\|data_json\|def.*questions" backend/app/{api,models,sampling}.py`) to expose spot fields.
- Test: `backend/tests/test_seed.py` (round-trip), `backend/tests/test_api.py` (serializer exposes fields).

**Interfaces:**
- Consumes: Task 1 validation.
- Produces: seeded spot question stores `{options_ar, correct_indices, chip_explanations_ar}` in `data_json`; `GET /questions` returns those for spot items (client checks locally).

- [ ] **Step 1: Write failing seed test** (`test_seed.py`) — add a spot question to `SAMPLE_DOC` (in `conftest.py`) and assert:

```python
def test_seed_stores_spot_indices(conn):
    from app.seed import seed_quiz
    doc = {"slug": "s2", "title_ar": "t", "pdf_filename": "x.pdf", "questions": [
        {"type": "spot", "prompt_ar": "p", "concept": "predatory_signs",
         "options_ar": ["a", "b", "c"], "correct_indices": [0, 2],
         "chip_explanations_ar": ["ea", "eb", "ec"]}]}
    qid = seed_quiz(conn, doc)
    import json
    row = conn.execute("SELECT data_json FROM questions WHERE quiz_id=?", (qid,)).fetchone()
    data = json.loads(row["data_json"])
    assert data["correct_indices"] == [0, 2]
    assert data["options_ar"] == ["a", "b", "c"]
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement in `seed.py`.** In the question-insert loop, where `data` is built per type, add spot handling so `data` includes `options_ar`, `correct_indices`, `chip_explanations_ar` (mirror how match/order pack their `data`).

- [ ] **Step 4: Expose in the `GET /questions` serializer.** For `spot`, include `options_ar`, `correct_indices`, and `chip_explanations_ar` in the returned dict (mirror how mcq returns `options_ar`/answer key + `option_explanations_ar`). Add/extend a test in `test_api.py` asserting a served spot question includes `correct_indices`.

- [ ] **Step 5: Run backend suite, expect PASS** — `cd backend && pytest -q`

- [ ] **Step 6: Commit** — `git commit -m "feat(seed/api): persist + expose spot data for client-side checking"`

---

### Task 3: curated journals application content

**Files:**
- Rewrite: `content/questions/journals.json` (7 application tasks per the spec §3).

- [ ] **Step 1: Replace `journals.json`** with the 7 tasks from spec §3 (`predatory-email-spotter` [spot, asset `assets/journals/predatory_email.png`], `quartile-venue-decision` [image, `journal_quartile.png`], `jane-finder-selection` [mcq, `journal_finder.jpg`], `fake-index-audit` [tf], `oa-models-matching` [match], `researcher-metric-choice` [mcq], `journal-vetting-sequence` [order]). Each: `concept`, `prompt_ar`, options/items, correct answer(s), `explanation_ar` (+ `option_explanations_ar`/`chip_explanations_ar`), `base_points`. Keep `slug:"journals"`, `title_ar`, `pdf_filename`.

- [ ] **Step 2: Validate** — `cd backend && python -c "import sys;sys.path.insert(0,'.');import json;from app.content_schema import validate_quiz;validate_quiz(json.load(open('../content/questions/journals.json',encoding='utf-8')));print('valid')"` → `valid`.

- [ ] **Step 3: Seed a scratch DB + sanity-check** the 7 load and types are `{spot,image,mcq,tf,match,order}`.

- [ ] **Step 4: Commit** — `git commit -m "feat(content): journals station -> 7 application tasks (application-first)"`

---

### Task 4: frontend `spot` runner (render + check)

**Files:**
- Modify: `frontend/app.js` (render + check `spot` in the runner), `frontend/styles.css` (chip styles).
- Test: `frontend/tests/spot.test.js` (new) or extend `runner.test.js`.

**Interfaces:**
- Consumes: served spot question `{id, type:"spot", prompt_ar, options_ar, correct_indices, chip_explanations_ar, asset_file?}`.
- Produces: a `renderSpot(q)`/branch in the runner that shows chips + a check button; `spotIsCorrect(selected, correct)` returns true on exact set-equality; wrong check increments retries (existing model), hint reveals remaining count.

- [ ] **Step 1: Write failing test** (`tests/spot.test.js`) — load `app.js` in jsdom (mirror `runner.test.js` setup) and assert a pure helper:

```javascript
import { ... } // mirror existing runner.test.js harness that evals app.js
it("spotIsCorrect requires exact set match", () => {
  expect(spotIsCorrect([2, 0], [0, 2])).toBe(true);   // order-independent
  expect(spotIsCorrect([0], [0, 2])).toBe(false);      // missing
  expect(spotIsCorrect([0, 1, 2], [0, 2])).toBe(false);// extra
});
```

- [ ] **Step 2: Run, expect FAIL** — `cd frontend && npx vitest run tests/spot.test.js`

- [ ] **Step 3: Implement** in `app.js`:
  - `function spotIsCorrect(sel, correct){ const a=new Set(sel), b=new Set(correct); return a.size===b.size && [...a].every(x=>b.has(x)); }`
  - In the question renderer, add a `type==="spot"` branch: render `q.options_ar` as toggle chips (`.spot-chip`, click toggles `.selected`), plus a check button `تحقّق`. On check: read selected indices; if `spotIsCorrect` → mark solved (advance like a correct answer); else increment `curRetries`, flash wrong chips, allow re-check. Hint button reveals `correct_indices.length - selectedCorrect` remaining (sets `curHint=true`). On solve, show `explanation_ar`. Reuse the existing submit/advance path so `{question_id, retries, hint_used}` flows unchanged.
  - Expose helper for tests (attach to window or export pattern used by existing tests).

- [ ] **Step 4: Add chip CSS** (`styles.css`): `.spot-chips{display:flex;flex-wrap:wrap;gap:8px}` `.spot-chip{padding:10px 14px;border-radius:12px;background:var(--card);border:1px solid var(--gold-dim);cursor:pointer}` `.spot-chip.selected{border-color:var(--cyan);box-shadow:0 0 10px #0ac8b955}` `.spot-chip.wrong{border-color:var(--bad);animation:shake .3s}`.

- [ ] **Step 5: Run frontend suite, expect PASS** — `cd frontend && npx vitest run`

- [ ] **Step 6: Commit** — `git commit -m "feat(runner): spot red-flag multi-select interaction"`

---

### Task 5: full verification + deploy

**Files:** none (ops).

- [ ] **Step 1: Full suite** — `./scripts/test.sh` (backend pytest + frontend vitest). All green.
- [ ] **Step 2: Playwright smoke** (via system Chrome per the Playwright rule): serve locally, load `/app/`, drive journals, screenshot a `spot` task; verify chips toggle + check works and artifacts render.
- [ ] **Step 3: Deploy** — `docker compose up -d --build web`, then re-seed journals:
  `docker compose exec -T web python -c "import sys;sys.path.insert(0,'.');from app.db import connect,init_schema;from app.seed import seed_all;c=connect('/data/quiz.db');init_schema(c);print(seed_all(c,'/srv/content/questions'))"`
- [ ] **Step 4: Verify live** — public tunnel serves fresh bundle; `GET /api/quizzes/journals/questions` returns the 7 applied tasks incl. the `spot` item with `correct_indices`.
- [ ] **Step 5: Commit** any residual (none expected). Note journals leaderboard reset.

---

## Self-Review

**Spec coverage:** spot interaction → Task 1+2+4; 7 tasks → Task 3; integration/reseed → Task 5; testing → each task + Task 5. ✓
**Placeholder scan:** schema/seed/frontend code is concrete; Task 2's exact serializer file is located via a grep command (real project's path) rather than guessed — the one intentional lookup. ✓
**Type consistency:** `correct_indices` (list[int]), `spotIsCorrect(sel, correct)`, `data_json` keys `{options_ar, correct_indices, chip_explanations_ar}` consistent across tasks. ✓

## Out of scope
Capstone journey; other 5 stations; free-form/rubric tasks; server-side answer verification.
