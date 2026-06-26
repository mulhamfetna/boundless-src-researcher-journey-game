# Phase 3A — Khan-Style Question Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn answering into a Khan-style learning loop — immediate per-option feedback, retry-until-correct without revealing the answer, hints, fun facts, and retry/hint-aware scoring.

**Architecture:** Client-side answer checking: `GET /questions` ships the answer keys + per-option explainers + hints + the quiz's fun facts; the Mini App runs the retry loop locally and `submit` reports `{retries, hint_used}` per question. The server scores authoritatively from retries/hints (no speed bonus). Schema gains `answers.retries/hint_used` and `quizzes.fun_facts_json`. The `speed_demon` badge becomes `self_reliant` (no hints).

**Tech Stack:** Python 3.14, FastAPI, stdlib sqlite3, python-telegram-bot, pytest; dependency-free RTL HTML/CSS/JS.

## Global Constraints

- **Client-side checking:** `GET /questions` exposes answer keys (`correct_index`/`correct_pairs`/`correct_sequence`), `option_explanations_ar`, `hint_ar`, and quiz `fun_facts_ar`. This is intentional — the Phase-1 "no leak" test is replaced.
- **Submit shape:** answer objects are `{question_id, retries, hint_used}`. The final answer is always correct (client only advances on solve); the server stores `is_correct=True` and the retries/hint.
- **Scoring:** `penalty = max(0.10, 1 − 0.25·retries − 0.20·(1 if hint_used else 0))`; `points = round(base × penalty × streak_multiplier(streak_before))`. **No speed bonus.** `first_try = retries==0 and not hint_used`; streak advances only on `first_try`; `accuracy = first_try_count / total_questions`.
- **Badges:** `perfect_quiz` (accuracy≥1.0), `streak_master` (max_streak≥5), `self_reliant` (hints_used==0), `first_finish`. Priority `perfect_quiz > streak_master > self_reliant > first_finish`. `self_reliant` Arabic label "بلا تلميحات", icon 🛡️.
- **Fun facts:** per-quiz `fun_facts_ar` list; runner shows one after every 5 answered questions.
- **Schema additions** (per question `data_json`): `option_explanations_ar: [str]` (mcq/tf/image; length == options length when present), `hint_ar: str`. Match/order may carry `hint_ar`.
- **Synthetic data allowed** for explainers/hints/fun-facts where the PDF doesn't supply them; mark illustrative.
- **Language:** Arabic, RTL. **Package root** `backend/app/`, tests from `backend/`. **Commit after every task.**

## Answer & payload shapes (single source of truth)

- Stored `data_json`: option types add `"option_explanations_ar": [...]`, `"hint_ar": "..."`; match adds `"hint_ar"` (keeps left/right/correct_pairs); order adds `"hint_ar"` (keeps items/correct_sequence).
- `quizzes.fun_facts_json`: JSON array of Arabic strings.
- `GET /questions` per item: existing fields + the type's answer key + `option_explanations_ar` (option types) + `hint_ar`; response root adds `"fun_facts_ar": [...]`.
- `submit` `payload["answers"]`: `[{"question_id", "retries", "hint_used"}]`.

---

### Task 1: Migration, schema, and `record_answer` columns

**Files:**
- Modify: `backend/app/db.py` (SCHEMA), `backend/app/migrate.py`, `backend/app/models.py` (`record_answer`)
- Modify: `backend/tests/test_migrate.py` (append)

**Interfaces:**
- Produces: `answers` has `retries`, `hint_used`; `quizzes` has `fun_facts_json`. `migrate()` returns those change keys when applied. `models.record_answer(conn, attempt_id, question_id, given, is_correct, time_ms, points, retries=0, hint_used=0)` persists the two new columns.

- [ ] **Step 1: Edit `backend/app/db.py` SCHEMA.** In the `answers` table add two columns after `points_awarded`:
```
    points_awarded INTEGER NOT NULL,
    retries        INTEGER NOT NULL DEFAULT 0,
    hint_used      INTEGER NOT NULL DEFAULT 0
```
In the `quizzes` table add a column after `display_order`:
```
    display_order INTEGER NOT NULL DEFAULT 0,
    fun_facts_json TEXT NOT NULL DEFAULT '[]'
```

- [ ] **Step 2: Append failing tests** to `backend/tests/test_migrate.py`

```python
def test_migrate_adds_retry_and_funfacts_columns(tmp_path):
    conn = _old_db(str(tmp_path / "old.db"))
    migrate(conn)
    acols = {r["name"] for r in conn.execute("PRAGMA table_info(answers)")}
    qcols = {r["name"] for r in conn.execute("PRAGMA table_info(quizzes)")}
    assert {"retries", "hint_used"} <= acols
    assert "fun_facts_json" in qcols
    # idempotent
    assert migrate(conn) == []
```

(The existing `_old_db`/`OLD_SCHEMA` in this file lack these columns, so the migration must add them.)

- [ ] **Step 3: Run it, expect failure**

Run: `cd backend && pytest tests/test_migrate.py::test_migrate_adds_retry_and_funfacts_columns -v`
Expected: FAIL — `retries`/`fun_facts_json` missing.

- [ ] **Step 4: Edit `backend/app/migrate.py`** — add these blocks inside `migrate()` before the `conn.commit()`:

```python
    if "retries" not in _columns(conn, "answers"):
        conn.execute("ALTER TABLE answers ADD COLUMN retries INTEGER NOT NULL DEFAULT 0")
        changes.append("answers.retries")
    if "hint_used" not in _columns(conn, "answers"):
        conn.execute("ALTER TABLE answers ADD COLUMN hint_used INTEGER NOT NULL DEFAULT 0")
        changes.append("answers.hint_used")
    if "fun_facts_json" not in _columns(conn, "quizzes"):
        conn.execute("ALTER TABLE quizzes ADD COLUMN fun_facts_json TEXT NOT NULL DEFAULT '[]'")
        changes.append("quizzes.fun_facts_json")
```

- [ ] **Step 5: Edit `backend/app/models.py` `record_answer`** to accept and store the new columns:

```python
def record_answer(conn, attempt_id, question_id, given, is_correct, time_ms, points, retries=0, hint_used=0):
    conn.execute(
        """INSERT INTO answers
           (attempt_id, question_id, given_json, is_correct, time_ms, points_awarded, retries, hint_used)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (attempt_id, question_id, json.dumps(given), int(is_correct), time_ms, points, int(retries), int(hint_used)),
    )
    conn.commit()
```

- [ ] **Step 6: Run tests, expect pass**

Run: `cd backend && pytest tests/test_migrate.py -v && pytest -q`
Expected: migration tests pass; full suite green (record_answer defaults keep existing callers working).

- [ ] **Step 7: Commit**

```bash
git add backend/app/db.py backend/app/migrate.py backend/app/models.py backend/tests/test_migrate.py
git commit -m "feat: schema for retries/hint_used + quiz fun_facts"
```

---

### Task 2: Scoring — `retry_penalty` and `score_retry`

**Files:**
- Modify: `backend/app/scoring.py`, `backend/tests/test_scoring.py` (append)

**Interfaces:**
- Consumes: existing `streak_multiplier`.
- Produces: `retry_penalty(retries: int, hint_used: bool) -> float`; `score_retry(base_points: int, retries: int, hint_used: bool, streak_before: int) -> int`.

- [ ] **Step 1: Append failing tests** to `backend/tests/test_scoring.py`

```python
from app.scoring import retry_penalty, score_retry


def test_retry_penalty_values():
    assert retry_penalty(0, False) == 1.0
    assert round(retry_penalty(1, False), 2) == 0.75
    assert round(retry_penalty(0, True), 2) == 0.80
    assert round(retry_penalty(1, True), 2) == 0.55
    assert retry_penalty(10, True) == 0.10  # floor


def test_score_retry():
    # first-try, no hint, no streak -> base
    assert score_retry(100, 0, False, 0) == 100
    # 1 retry -> 75, streak 0
    assert score_retry(100, 1, False, 0) == 75
    # hint -> 80 * streak 1.2 (streak 2) = 96
    assert score_retry(100, 0, True, 2) == 96
```

- [ ] **Step 2: Run, expect failure**

Run: `cd backend && pytest tests/test_scoring.py -k "retry" -v`
Expected: FAIL — `ImportError: cannot import name 'retry_penalty'`.

- [ ] **Step 3: Append to `backend/app/scoring.py`**

```python
def retry_penalty(retries: int, hint_used: bool) -> float:
    return max(0.10, 1.0 - 0.25 * retries - 0.20 * (1 if hint_used else 0))


def score_retry(base_points: int, retries: int, hint_used: bool, streak_before: int) -> int:
    return round(base_points * retry_penalty(retries, hint_used) * streak_multiplier(streak_before))
```

- [ ] **Step 4: Run, expect pass**

Run: `cd backend && pytest tests/test_scoring.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/app/scoring.py backend/tests/test_scoring.py
git commit -m "feat: retry/hint-aware scoring"
```

---

### Task 3: Content schema — explainers, hint, fun facts

**Files:**
- Modify: `backend/app/content_schema.py`, `backend/tests/test_content_schema.py` (append)

**Interfaces:**
- Produces: `validate_quiz` accepts optional `option_explanations_ar` (option types; length == options), `hint_ar` (str), and quiz-level `fun_facts_ar` (list of str).

- [ ] **Step 1: Append failing tests** to `backend/tests/test_content_schema.py`

```python
def test_option_explanations_length_must_match():
    doc = _good_doc()
    doc["questions"][0]["option_explanations_ar"] = ["a", "b"]  # 2 != 4 options
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_valid_explanations_hint_funfacts_pass():
    doc = _good_doc()
    doc["fun_facts_ar"] = ["معلومة"]
    q = doc["questions"][0]
    q["option_explanations_ar"] = ["خطأ", "خطأ", "صحيح", "خطأ"]
    q["hint_ar"] = "تلميح"
    validate_quiz(doc)


def test_funfacts_must_be_list_of_str():
    doc = _good_doc()
    doc["fun_facts_ar"] = "ليست قائمة"
    with pytest.raises(SchemaError):
        validate_quiz(doc)
```

- [ ] **Step 2: Run, expect failure**

Run: `cd backend && pytest tests/test_content_schema.py -k "explanations or funfacts" -v`
Expected: FAIL (no validation yet).

- [ ] **Step 3: Edit `backend/app/content_schema.py`** — in `validate_quiz`, after the `questions` non-empty check, add the quiz-level fun-facts check:

```python
    if "fun_facts_ar" in doc:
        _require(isinstance(doc["fun_facts_ar"], list)
                 and all(isinstance(x, str) for x in doc["fun_facts_ar"]),
                 "fun_facts_ar must be a list of strings")
```

Inside the per-question loop, after the type-specific blocks (before the `if "asset" in q:` block), add:

```python
        if "option_explanations_ar" in q:
            _require(q["type"] in ("mcq", "tf", "image"),
                     f"{where}: option_explanations_ar only valid for option types")
            _require(isinstance(q["option_explanations_ar"], list)
                     and len(q["option_explanations_ar"]) == len(q.get("options_ar", [])),
                     f"{where}: option_explanations_ar length must equal options_ar")
        if "hint_ar" in q:
            _require(isinstance(q["hint_ar"], str), f"{where}: hint_ar must be a string")
```

- [ ] **Step 4: Run, expect pass**

Run: `cd backend && pytest tests/test_content_schema.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/app/content_schema.py backend/tests/test_content_schema.py
git commit -m "feat: validate option explainers, hint, fun facts"
```

---

### Task 4: Seed — persist explainers, hint, fun facts

**Files:**
- Modify: `backend/app/seed.py`, `backend/tests/test_seed.py` (append)

**Interfaces:**
- Produces: `seed_quiz` stores `option_explanations_ar` + `hint_ar` in `data_json` (per type) and the quiz's `fun_facts_ar` into `quizzes.fun_facts_json`.

- [ ] **Step 1: Append failing test** to `backend/tests/test_seed.py`

```python
import json as _json2
from app.models import get_quiz_by_slug as _gqs


def test_seed_stores_explainers_hint_funfacts(conn):
    doc = {
        "slug": "kx", "title_ar": "t", "pdf_filename": "f.pdf",
        "fun_facts_ar": ["حقيقة 1", "حقيقة 2"],
        "questions": [{
            "type": "mcq", "prompt_ar": "س", "options_ar": ["أ", "ب", "ج", "د"],
            "correct_index": 2, "option_explanations_ar": ["لا", "لا", "نعم", "لا"], "hint_ar": "فكّر",
        }],
    }
    seed_quiz(conn, doc)
    quiz = _gqs(conn, "kx")
    assert _json2.loads(quiz["fun_facts_json"]) == ["حقيقة 1", "حقيقة 2"]
    q = get_questions(conn, quiz["id"])[0]
    data = _json2.loads(q["data_json"])
    assert data["option_explanations_ar"][2] == "نعم"
    assert data["hint_ar"] == "فكّر"
```

- [ ] **Step 2: Run, expect failure**

Run: `cd backend && pytest tests/test_seed.py -k explainers -v`
Expected: FAIL — `KeyError: 'fun_facts_json'` / explainers not stored.

- [ ] **Step 3: Edit `backend/app/seed.py`.** Update the quiz INSERT to include `fun_facts_json`:

```python
    cur = conn.execute(
        "INSERT INTO quizzes (slug, title_ar, pdf_filename, display_order, fun_facts_json) VALUES (?, ?, ?, ?, ?)",
        (doc["slug"], doc["title_ar"], doc["pdf_filename"], doc.get("display_order", 0),
         json.dumps(doc.get("fun_facts_ar", []), ensure_ascii=False)),
    )
```

In the per-question loop, after building `data` per type, attach the optional fields:

```python
        if q["type"] in ("mcq", "tf", "image") and "option_explanations_ar" in q:
            data["option_explanations_ar"] = q["option_explanations_ar"]
        if "hint_ar" in q:
            data["hint_ar"] = q["hint_ar"]
```

- [ ] **Step 4: Run, expect pass**

Run: `cd backend && pytest tests/test_seed.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/app/seed.py backend/tests/test_seed.py
git commit -m "feat: seed explainers, hint, and quiz fun facts"
```

---

### Task 5: Badges — `self_reliant` replaces `speed_demon`

**Files:**
- Modify: `backend/app/badges.py`, `backend/app/report.py` (`_BADGE_AR`), `backend/tests/test_badges.py`

**Interfaces:**
- Produces: `evaluate(summary)` awards `self_reliant` when `summary["hints_used"] == 0`; `ALL_CODES`/`_PRIORITY`/`top_badge` use `self_reliant`. `report._BADGE_AR` maps `self_reliant`.

- [ ] **Step 1: Update `backend/tests/test_badges.py`** — replace `speed_demon` references with the new rule. Change `test_evaluate_all_conditions` and `test_evaluate_thresholds` to:

```python
def test_evaluate_all_conditions():
    s = {"accuracy": 1.0, "max_streak": 6, "hints_used": 0, "is_first_finish": True}
    assert set(evaluate(s)) == {"perfect_quiz", "streak_master", "self_reliant", "first_finish"}


def test_self_reliant_only_with_zero_hints():
    assert "self_reliant" in evaluate({"accuracy": 0, "max_streak": 0, "hints_used": 0, "is_first_finish": False})
    assert "self_reliant" not in evaluate({"accuracy": 0, "max_streak": 0, "hints_used": 3, "is_first_finish": False})
```

(Remove the old `test_evaluate_thresholds` speed assertions; keep `test_evaluate_none` but update its summary to `{"accuracy":0.5,"max_streak":2,"hints_used":1,"is_first_finish":False}`. Update `test_top_badge_priority` if it referenced `speed_demon` — use `self_reliant`.)

- [ ] **Step 2: Run, expect failure**

Run: `cd backend && pytest tests/test_badges.py -v`
Expected: FAIL — `self_reliant` not produced.

- [ ] **Step 3: Edit `backend/app/badges.py`**

```python
ALL_CODES = ["perfect_quiz", "self_reliant", "streak_master", "first_finish"]
_PRIORITY = ["perfect_quiz", "streak_master", "self_reliant", "first_finish"]
STREAK_MASTER_MIN = 5
```
(Remove `SPEED_DEMON_MIN_AVG_BONUS`.) Replace the speed clause in `evaluate`:

```python
    if summary.get("hints_used", 1) == 0:
        codes.append("self_reliant")
```
(Default `1` so a missing key does NOT award it.)

- [ ] **Step 4: Edit `backend/app/report.py` `_BADGE_AR`** — replace the `speed_demon` entry:

```python
    "self_reliant": "🛡️بلا تلميحات",
```

- [ ] **Step 5: Run, expect pass**

Run: `cd backend && pytest tests/test_badges.py tests/test_report.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/badges.py backend/app/report.py backend/tests/test_badges.py
git commit -m "feat: self_reliant badge replaces speed_demon"
```

---

### Task 6: API + report — expose keys/explainers/hint/fun-facts; submit on retries/hints

**Files:**
- Modify: `backend/app/api.py`, `backend/app/report.py`, `backend/tests/test_api.py`, `backend/tests/test_report.py`

**Interfaces:**
- Consumes: `scoring.score_retry`, `badges.evaluate/award`, `models.record_answer(..., retries, hint_used)`, `models.set_attempt_max_streak`.
- Produces: `GET /questions` exposes answer key + `option_explanations_ar` + `hint_ar` per item and `fun_facts_ar` at root; `submit` consumes `{question_id, retries, hint_used}`; `build_report` items include `retries`/`hint_used`/`first_try`.

- [ ] **Step 1: Update `get_questions` in `backend/app/api.py`** to expose the new fields. Replace the per-question `item` build with:

```python
    out = []
    funfacts = json.loads(quiz["fun_facts_json"]) if quiz["fun_facts_json"] else []
    for q in models.get_questions(conn, quiz["id"]):
        data = json.loads(q["data_json"])
        asset = models.get_asset_for_question(conn, q["id"])
        item = {
            "id": q["id"], "type": q["type"], "prompt_ar": q["prompt_ar"],
            "base_points": q["base_points"], "asset_file": asset["file_path"] if asset else None,
            "hint_ar": data.get("hint_ar", ""),
        }
        if q["type"] in ("mcq", "tf", "image"):
            item["options_ar"] = data["options_ar"]
            item["correct_index"] = data["correct_index"]
            item["option_explanations_ar"] = data.get("option_explanations_ar", [])
        elif q["type"] == "match":
            item["left_ar"] = data["left_ar"]; item["right_ar"] = data["right_ar"]
            item["correct_pairs"] = data["correct_pairs"]
        elif q["type"] == "order":
            item["items_ar"] = data["items_ar"]; item["correct_sequence"] = data["correct_sequence"]
        out.append(item)
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]},
            "questions": out, "fun_facts_ar": funfacts}
```

- [ ] **Step 2: Replace the scoring loop in `submit`** (the `for a in answers:` block and the summary) with the retry-based version:

```python
    total = 0
    first_try_count = 0
    streak = 0
    max_streak = 0
    hints_used = 0
    answers = payload.get("answers", [])
    for a in answers:
        qid = a.get("question_id")
        q = qrows.get(qid)
        if not q:
            continue
        retries = int(a.get("retries", 0))
        hint_used = bool(a.get("hint_used", False))
        first_try = retries == 0 and not hint_used
        pts = score_retry(q["base_points"], retries, hint_used, streak)
        streak = streak + 1 if first_try else 0
        max_streak = max(max_streak, streak)
        if first_try:
            first_try_count += 1
        if hint_used:
            hints_used += 1
        total += pts
        models.record_answer(conn, attempt_id, qid, {"retries": retries, "hint_used": hint_used},
                             True, 0, pts, retries=retries, hint_used=int(hint_used))

    total_questions = len(qrows)
    accuracy = first_try_count / total_questions if total_questions else 0.0
    models.finish_attempt(conn, attempt_id, total, accuracy, int(payload.get("duration_ms", 0)), _now(conn))
    models.set_attempt_max_streak(conn, attempt_id, max_streak)

    summary = {"accuracy": accuracy, "max_streak": max_streak,
               "hints_used": hints_used, "is_first_finish": is_first_finish}
    earned_now = badges.award(conn, contestant_id, badges.evaluate(summary), _now(conn))
```

Update the scoring import at the top of `api.py`:
```python
from app.scoring import grade, score_fraction, speed_bonus, score_retry
```

- [ ] **Step 3: Update `build_report` in `backend/app/report.py`** to surface retries/hint and not depend on a submitted answer. Replace the per-answer item build inside the loop with:

```python
        your_ar, correct_ar = _describe(q["type"], data, {})
        items.append({
            "type": q["type"], "prompt_ar": q["prompt_ar"], "is_correct": bool(ans["is_correct"]),
            "correct_ar": correct_ar, "retries": ans["retries"], "hint_used": bool(ans["hint_used"]),
            "first_try": ans["retries"] == 0 and not ans["hint_used"],
            "explanation_ar": q["explanation_ar"], "source_page": q["source_page"],
            "asset_file": asset["file_path"] if asset else None,
        })
```

(The `given = json.loads(ans["given_json"])` line and `your_ar` may stay; `_describe(..., {})` returns the correct side regardless.)

- [ ] **Step 4: Update the affected tests.**

In `backend/tests/test_api.py`:
- Rename `test_get_questions_hides_correct_index` → `test_get_questions_exposes_answer_key` and change its body to assert the key IS present:
```python
def test_get_questions_exposes_answer_key(api_client):
    body = api_client.get("/api/quizzes/journals/questions").json()
    assert "correct_index" in body["questions"][0]
    assert "fun_facts_ar" in body
```
- In `test_submit_scores_and_returns_report`, change each answer object from `{"question_id", "index", "time_ms"}` to `{"question_id": qid, "retries": 0, "hint_used": False}`, and assert `report["total_score"] > 0` and all items `is_correct`.
- In `test_submit_order_partial_and_first_finish_badge`, change the answer to `{"question_id": oq["id"], "retries": 0, "hint_used": False}`; it now earns `first_finish` and (zero hints) `self_reliant`; assert `"first_finish" in body["earned_now"]`.
- In `test_partial_submission_does_not_earn_perfect`, change the single answer to `{"question_id": oq["id"], "retries": 0, "hint_used": False}` and keep asserting `perfect_quiz` NOT earned and `accuracy < 1.0` (one of three questions answered).
- In `test_leaderboard_after_submit` / `test_overall_leaderboard`, change answer objects to the retries/hint shape.

In `backend/tests/test_report.py`:
- The two Phase-2A report tests record answers via `record_answer(conn, aid, qid, {...}, True, 1000, 150)` — they still pass (defaults retries=0). Update assertions that referenced `your_ar`/`given_index` to use `correct_ar`/`retries`. Specifically, in `test_build_report_shape` assert `report["items"][0]["first_try"] is True` and `"retries" in report["items"][0]`.

- [ ] **Step 5: Run the suites, expect pass**

Run: `cd backend && pytest tests/test_api.py tests/test_report.py -v && pytest -q`
Expected: all green, output pristine.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api.py backend/app/report.py backend/tests/test_api.py backend/tests/test_report.py
git commit -m "feat: questions expose keys/explainers/hint/funfacts; submit on retries/hints"
```

---

### Task 7: Frontend — Khan-style runner (retry, hint, match/order highlight, fun facts)

**Files:**
- Modify: `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`

**Interfaces:**
- Consumes the new `GET /questions` (answer keys, `option_explanations_ar`, `hint_ar`, `fun_facts_ar`) and `submit` shape `{question_id, retries, hint_used}`.

- [ ] **Step 1: Add markup** to `frontend/index.html` inside `screen-runner` — a hint button and a fun-fact overlay. After `<div id="q-options"></div>` add:
```html
      <button id="q-hint-btn" class="hint-btn">💡 تلميح</button>
      <div id="q-hint" class="hint-box hidden"></div>
      <div id="q-feedback" class="feedback-box"></div>
    </section>

    <section id="screen-funfact" class="screen hidden">
      <h2>💡 معلومة</h2>
      <div id="funfact-text"></div>
      <button id="funfact-continue">متابعة</button>
```
(Place the new `screen-funfact` section right after `screen-runner` closes; ensure the `</section>` above matches.)

- [ ] **Step 2: Add styles** to `frontend/styles.css` (append):
```css
.hint-btn { background:#3a3f55; margin-top:10px; }
.hint-box { background:#2a2f45; border-radius:10px; padding:10px; margin-top:8px; }
.feedback-box { margin-top:10px; min-height:1.2em; }
.opt.wrong { background:var(--bad); opacity:.7; }
.opt.correct { background:var(--good); }
.opt:disabled { cursor:default; }
.opt-explain { font-size:.9rem; color:#cdd3e6; margin:4px 0 8px; }
#screen-funfact { text-align:center; }
#funfact-text { background:var(--card); border-radius:12px; padding:18px; margin:12px 0; font-size:1.05rem; }
.slot.wrong, .order-row.wrong { outline:2px solid var(--bad); }
.slot.correct, .order-row.correct { outline:2px solid var(--good); }
```

- [ ] **Step 3: Add `"funfact"` to the `screens` array** in `frontend/app.js`:
```javascript
const screens = ["home", "runner", "report", "board", "badges", "funfact"];
```

- [ ] **Step 4: Replace the mcq/tf/image option rendering + `answer()`** in `frontend/app.js` with the Khan retry version. In `renderQuestion`, the `else` branch (option types) becomes:

```javascript
  else {
    const opts = document.getElementById("q-options");
    opts.innerHTML = "";
    document.getElementById("q-feedback").textContent = "";
    q.options_ar.forEach((text, i) => {
      const btn = document.createElement("button");
      btn.className = "opt";
      btn.textContent = text;
      btn.onclick = () => pickOption(btn, i);
      opts.appendChild(btn);
    });
  }
```

Add the hint + per-question state setup at the top of `renderQuestion` (after `const q = state.questions[state.idx];`):

```javascript
  state.curRetries = 0;
  state.curHint = false;
  const hintBtn = document.getElementById("q-hint-btn");
  const hintBox = document.getElementById("q-hint");
  hintBox.classList.add("hidden");
  if (q.hint_ar) {
    hintBtn.classList.remove("hidden");
    hintBtn.onclick = () => { hintBox.textContent = q.hint_ar; hintBox.classList.remove("hidden"); state.curHint = true; };
  } else {
    hintBtn.classList.add("hidden");
  }
```

Replace the old `answer(index)` function with:

```javascript
function pickOption(btn, index) {
  const q = state.questions[state.idx];
  if (index === q.correct_index) {
    btn.classList.add("correct");
    btn.disabled = true;
    const fb = document.getElementById("q-feedback");
    fb.textContent = "✅ " + (q.option_explanations_ar[index] || "إجابة صحيحة");
    recordAndAdvance(q);
  } else {
    btn.classList.add("wrong");
    btn.disabled = true;
    state.curRetries += 1;
    const ex = document.createElement("div");
    ex.className = "opt-explain";
    ex.textContent = "❌ " + (q.option_explanations_ar[index] || "إجابة غير صحيحة، حاول مرة أخرى");
    btn.insertAdjacentElement("afterend", ex);
  }
}

function recordAndAdvance(q) {
  state.answers.push({ question_id: q.id, retries: state.curRetries, hint_used: state.curHint });
  setTimeout(() => nextStep(), 700);
}

function nextStep() {
  state.idx += 1;
  if (state.idx > 0 && state.idx % 5 === 0 && state.idx < state.questions.length && state.funFacts.length) {
    showFunFact();
  } else if (state.idx < state.questions.length) {
    renderQuestion();
  } else {
    submit();
  }
}

function showFunFact() {
  const fact = state.funFacts[(Math.floor(state.idx / 5) - 1) % state.funFacts.length];
  document.getElementById("funfact-text").textContent = fact;
  document.getElementById("funfact-continue").onclick = () => {
    if (state.idx < state.questions.length) renderQuestion(); else submit();
  };
  show("funfact");
}
```

- [ ] **Step 5: Update `startQuiz` and `submit`.** In `startQuiz`, capture fun facts and init counters:
```javascript
async function startQuiz(slug) {
  const data = await api(`/quizzes/${slug}/questions`);
  state = { slug, questions: data.questions, funFacts: data.fun_facts_ar || [], idx: 0, answers: [], startedAt: Date.now() };
  renderQuestion();
  show("runner");
}
```
In `submit`, the body now sends the accumulated `state.answers` (already the retries/hint shape) — keep the existing POST but ensure no `time_ms` is required:
```javascript
async function submit() {
  const report = await api(`/quizzes/${state.slug}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData },
    body: JSON.stringify({ answers: state.answers, duration_ms: Date.now() - state.startedAt }),
  });
  renderReport(report);
  show("report");
}
```

- [ ] **Step 6: Update match/order to retry-highlight.** Replace `ensureSubmitButton`'s submit callback usage so that on "تأكيد" it CHECKS against the key client-side instead of immediately advancing. Replace `answerComplex` with `checkComplex`:

```javascript
function checkComplex(givenExtra) {
  const q = state.questions[state.idx];
  let correct;
  if (q.type === "order") {
    const seq = givenExtra.sequence;
    correct = q.correct_sequence.every((v, i) => seq[i] === v);
    if (!correct) {
      state.curRetries += 1;
      const rows = [...document.querySelectorAll(".order-row")];
      rows.forEach((r, i) => r.classList.toggle("wrong", Number(r.dataset.orig) !== q.correct_sequence[i]));
      return;
    }
  } else { // match
    const want = new Set(q.correct_pairs.map(p => p.join(",")));
    const have = givenExtra.pairs;
    correct = have.length === want.size && have.every(p => want.has(p.join(",")));
    if (!correct) {
      state.curRetries += 1;
      document.querySelectorAll(".slot").forEach(slot => {
        const chip = slot.querySelector(".chip");
        const ok = chip && want.has([slot.dataset.left, chip.dataset.right].join(","));
        slot.classList.toggle("wrong", !ok);
      });
      return;
    }
  }
  state.answers.push({ question_id: q.id, retries: state.curRetries, hint_used: state.curHint });
  nextStep();
}
```

Change `renderMatch`/`renderOrder`'s `ensureSubmitButton(() => { ... answerComplex({...}) })` calls to call `checkComplex({...})` instead (same `{pairs}` / `{sequence}` payloads). Remove the now-unused `answerComplex`.

- [ ] **Step 7: Update the badges map** in `frontend/app.js` — replace `speed_demon` with `self_reliant`:
```javascript
const BADGES = {
  perfect_quiz: { ico: "🏅", name_ar: "الإتقان" },
  self_reliant: { ico: "🛡️", name_ar: "بلا تلميحات" },
  streak_master: { ico: "🔥", name_ar: "السلسلة" },
  first_finish: { ico: "🌟", name_ar: "البداية" },
};
const BADGE_ORDER = ["perfect_quiz", "self_reliant", "streak_master", "first_finish"];
```
And update `renderReport`'s per-item lines to show tries/hint instead of your_ar/given (since the new report items have `retries`/`hint_used`/`correct_ar`/`first_try`):
```javascript
    const tries = it.first_try ? "من أول محاولة ✅" : `محاولات: ${it.retries + 1}${it.hint_used ? " · استُخدم تلميح" : ""}`;
    div.className = "report-item " + (it.first_try ? "good" : "bad");
    div.innerHTML =
      `<div>${it.prompt_ar}</div>` +
      `<div>${tries}</div>` +
      `<div>الصحيح: ${it.correct_ar}</div>` +
      (it.explanation_ar ? `<div>📖 ${it.explanation_ar}` + (it.source_page ? ` (ص ${it.source_page})` : "") + `</div>` : "") +
      (it.asset_file ? `<img src="/content/${it.asset_file}" alt="" />` : "");
```

- [ ] **Step 8: Verify** — `node --check frontend/app.js` (exit 0). Serve and load:
```bash
cd backend && (source ../.venv/bin/activate 2>/dev/null; QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --port 8013 &); sleep 3
curl -s -o /dev/null -w "app=%{http_code}\n" http://localhost:8013/app/
pkill -f "uvicorn app.main:app --port 8013"
```
Expected: `node --check` clean; `/app/` 200. (Full retry/hint/fun-fact flow verified in Telegram in Task 12.)

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: Khan-style runner (retry, hint, match/order highlight, fun facts)"
```

---

### Task 8: Content retrofit — `journals`

**Files:**
- Modify: `content/questions/journals.json`

**Interfaces:**
- Produces: every question in `journals.json` gains `option_explanations_ar` (option types) + `hint_ar`; the quiz gains `fun_facts_ar` (≥3). Still passes `validate_quiz`.

- [ ] **Step 1: Read `content/questions/journals.json`.** For EACH `mcq`/`tf`/`image` question add `option_explanations_ar` (one entry per option: for wrong options, a one-sentence reason it's wrong; for the correct option, a confirming sentence) and a `hint_ar`. For each `match`/`order` question add a `hint_ar`. Ground explanations in the journals concepts (indexing, quartiles, impact factor, predatory red flags); synthetic-but-accurate is fine, mark nothing as real-sourced. Add a quiz-level `fun_facts_ar` array with ≥3 short Arabic facts about scientific journals.

- [ ] **Step 2: Validate**
```bash
cd backend && (source ../.venv/bin/activate 2>/dev/null; python -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/journals.json',encoding='utf-8'))); print('valid')")
```
Expected: `valid`. Spot-check that every option type has `option_explanations_ar` with length == its options and a `hint_ar`, and the quiz has `fun_facts_ar`.

- [ ] **Step 3: Commit**
```bash
git add content/questions/journals.json
git commit -m "content: explainers/hints/fun-facts for journals"
```

---

### Task 9: Content retrofit — `foundations`

**Files:** Modify `content/questions/foundations.json`

- [ ] **Step 1:** Same as Task 8 Step 1, for `content/questions/foundations.json` (concepts: research foundations, research gap, literature review, originality). Add per-option explainers + hints to every question and a ≥3-entry `fun_facts_ar`.
- [ ] **Step 2:** Validate (same command, `foundations.json`) → `valid`.
- [ ] **Step 3:** Commit `content: explainers/hints/fun-facts for foundations`.

---

### Task 10: Content retrofit — `paper-types`

**Files:** Modify `content/questions/paper-types.json`

- [ ] **Step 1:** Same retrofit for `content/questions/paper-types.json` (concepts: paper types, review types, evidence levels). Per-option explainers + hints on every question, ≥3 `fun_facts_ar`.
- [ ] **Step 2:** Validate → `valid`.
- [ ] **Step 3:** Commit `content: explainers/hints/fun-facts for paper-types`.

---

### Task 11: Content retrofit — `paper-parts`

**Files:** Modify `content/questions/paper-parts.json`

- [ ] **Step 1:** Same retrofit for `content/questions/paper-parts.json` (concepts: IMRaD sections and their purposes). Per-option explainers + hints on every question, ≥3 `fun_facts_ar`.
- [ ] **Step 2:** Validate → `valid`.
- [ ] **Step 3:** Commit `content: explainers/hints/fun-facts for paper-parts`.

---

### Task 12: Live deploy + verify

**Files:** none (operational).

- [ ] **Step 1:** Validate all four files:
```bash
cd backend && source ../.venv/bin/activate 2>/dev/null
for f in ../content/questions/*.json; do python -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('$f',encoding='utf-8'))); print('valid', '$f')"; done; cd ..
```
- [ ] **Step 2:** `docker compose build web bot`
- [ ] **Step 3:** Migrate: `docker compose run --rm web python -m app.migrate` → expect `['answers.retries', 'answers.hint_used', 'quizzes.fun_facts_json']` (or `already current` on reruns).
- [ ] **Step 4:** Re-seed all: `docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect; from app.seed import seed_all; c=connect('/data/quiz.db'); print('seeded', seed_all(c, '/srv/content/questions'))"`
- [ ] **Step 5:** Restart + verify:
```bash
docker compose up -d web bot cloudflared
curl -s "https://src.mulhamfetna.com/api/quizzes/journals/questions" | python3 -c "import sys,json; d=json.load(sys.stdin); q=d['questions'][0]; print('has key/explain/hint:', 'correct_index' in q, bool(q.get('option_explanations_ar')), 'hint_ar' in q); print('funfacts:', len(d['fun_facts_ar']))"
```
Expected: keys + explainers + hint exposed; fun facts present.
- [ ] **Step 6: End-to-end (manual, Telegram):** wrong option → red + explainer, retry until correct (right one never pre-highlighted); تلميح reveals a hint; match/order wrong items flash, fix + resubmit; fun-fact card after 5; report shows tries/hint; `self_reliant` badge earned on a no-hint run.

---

## Self-Review (completed by plan author)

**Spec coverage:** schema (Task 3), data model + migration (Task 1), scoring (Task 2), badges self_reliant (Task 5), API expose + submit (Task 6), report (Task 6), runner UX incl. hint/retry/match-order-highlight/fun-facts (Task 7), content retrofit all 51 + fun-facts (Tasks 8–11), deploy (Task 12). ✓

**Placeholder scan:** No "TBD/handle errors" in code steps. Content tasks (8–11) are authoring, bounded by `validate_quiz` and explicit per-option/hint/fun-fact requirements.

**Type consistency:** `retry_penalty`/`score_retry` used in Task 2 + Task 6. `record_answer(..., retries, hint_used)` defined in Task 1, used in Task 6. submit answer shape `{question_id, retries, hint_used}` consistent across Task 6 (backend) and Task 7 (frontend) and the updated tests. `option_explanations_ar`/`hint_ar`/`fun_facts_ar` consistent across schema (3), seed (4), API (6), frontend (7), content (8–11). Badge `self_reliant` consistent in badges.py (5), report `_BADGE_AR` (5), frontend BADGES (7).

## Out of scope
- 3B (applied/synthetic bank + random no-repeat sampling), 3C (dashboard). No auth/hosting change.
```
