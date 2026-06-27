# Phase 3C — Khan-Style Learner Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a personal "تقدّمي" dashboard to the Mini App showing per-concept mastery, progress stats, activity history, and what-to-do-next nudges.

**Architecture:** A new pure `app/progress.py` computes mastery (recent first-try accuracy per concept), stats, and next-steps from the learner's answers. New `app/models.py` queries gather a contestant's answers and attempts (concept read from `data_json` in Python — no JSON1 dependency). A new authenticated `GET /api/me/dashboard` assembles the payload. A new RTL `screen-progress` renders it. No DB migration; reads existing data.

**Tech Stack:** Python 3.14, FastAPI, stdlib `sqlite3`, pytest. Dependency-free HTML/CSS/JS frontend with the Telegram WebApp SDK.

## Global Constraints

- **Mastery metric:** first-try accuracy, where `first_try = retries == 0 and not hint_used`.
- **Recency window:** the most recent **5** answers per concept (`recent_n = 5`).
- **Levels (4):** `not_started` (0 answers) · `familiar` (rate < 0.50) · `proficient` (0.50 ≤ rate < 0.85) · `mastered` (rate ≥ 0.85 **and** kept ≥ 3).
- **Compute server-side, recompute-on-read.** No materialized table, no DB migration.
- **Concept labels** live in code (`progress.CONCEPT_LABELS_AR`); a missing slug falls back to itself.
- **Auth:** `GET /api/me/dashboard` validates Telegram `initData` (401 on failure / missing user), same pattern as `/me/badges`.
- **Language:** all learner-facing copy is **Arabic, RTL**.
- **`hints_used`** is computed from the answer set (the `attempts` table has no hint column).
- **Dashboard includes every concept of every quiz** — concepts with no answers show as `not_started`.
- Tests run from `backend/` with `pytest`. The frontend asset version is auto-stamped by `main.py` (no manual `?v=` bump needed).

---

## File Structure

```
backend/app/
  progress.py     # CREATE: pure mastery/stats/next-steps + CONCEPT_LABELS_AR
  models.py       # MODIFY: get_contestant_answers, get_contestant_attempts, quiz_of_concept
  api.py          # MODIFY: GET /api/me/dashboard
backend/tests/
  test_progress.py        # CREATE
  test_models_dashboard.py # CREATE
  test_api.py             # MODIFY: dashboard endpoint tests
frontend/
  index.html      # MODIFY: screen-progress section + home button
  app.js          # MODIFY: LEVELS map, loadDashboard(), wire button, add "progress" screen
  styles.css      # MODIFY: mastery chip + dashboard styles
```

---

### Task 1: Mastery engine — `app/progress.py`

**Files:**
- Create: `backend/app/progress.py`, `backend/tests/test_progress.py`

**Interfaces:**
- Produces:
  - `first_try_of(answer: dict) -> bool` — `int(answer.get("retries",0)) == 0 and not answer.get("hint_used")`.
  - `level_for(rate: float, count: int) -> str` — returns one of `not_started|familiar|proficient|mastered` per Global Constraints.
  - `mastery_for_concepts(answers: list[dict], recent_n: int = 5) -> dict[str, dict]` — each answer has `concept`, `retries`, `hint_used`, `order` (higher = more recent). Returns `{concept: {"rate", "count", "level"}}`. Only concepts present in `answers`.
  - `summarize_stats(attempts: list[dict]) -> dict` — `{total_points, attempts_count, best_by_quiz, best_streak, first_try_accuracy}`; empty → zeros.
  - `next_steps(mastery: dict, quiz_of_concept: dict[str, dict], limit: int = 2) -> list[dict]`.
  - `CONCEPT_LABELS_AR: dict[str, str]`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_progress.py`

```python
from app.progress import (
    first_try_of, level_for, mastery_for_concepts, summarize_stats,
    next_steps, CONCEPT_LABELS_AR,
)


def test_first_try_of():
    assert first_try_of({"retries": 0, "hint_used": 0}) is True
    assert first_try_of({"retries": 1, "hint_used": 0}) is False
    assert first_try_of({"retries": 0, "hint_used": 1}) is False


def test_level_for_boundaries():
    assert level_for(0.0, 0) == "not_started"
    assert level_for(0.0, 2) == "familiar"
    assert level_for(0.49, 5) == "familiar"
    assert level_for(0.50, 5) == "proficient"
    assert level_for(0.84, 5) == "proficient"
    assert level_for(0.85, 3) == "mastered"
    assert level_for(1.0, 2) == "proficient"  # >=0.85 but <3 answers -> not mastered


def _ans(concept, order, retries=0, hint=0):
    return {"concept": concept, "order": order, "retries": retries, "hint_used": hint}


def test_mastery_uses_only_recent_n():
    # 6 answers for concept 'x': 5 oldest wrong, 1 newest right -> recent 5 = 4 wrong + 1 right
    answers = [_ans("x", i, retries=1) for i in range(5)] + [_ans("x", 5, retries=0)]
    m = mastery_for_concepts(answers, recent_n=5)["x"]
    assert m["count"] == 5
    assert abs(m["rate"] - 0.2) < 1e-9  # 1 of last 5 first-try
    assert m["level"] == "familiar"


def test_mastery_mastered_when_recent_all_first_try():
    answers = [_ans("y", i) for i in range(4)]  # all first-try
    m = mastery_for_concepts(answers)["y"]
    assert m["level"] == "mastered"


def test_summarize_stats_empty():
    s = summarize_stats([])
    assert s == {"total_points": 0, "attempts_count": 0, "best_by_quiz": {},
                 "best_streak": 0, "first_try_accuracy": 0.0}


def test_summarize_stats_aggregates():
    attempts = [
        {"quiz_slug": "a", "total_score": 100, "accuracy": 0.8, "max_streak": 3},
        {"quiz_slug": "a", "total_score": 150, "accuracy": 1.0, "max_streak": 5},
        {"quiz_slug": "b", "total_score": 60, "accuracy": 0.6, "max_streak": 2},
    ]
    s = summarize_stats(attempts)
    assert s["total_points"] == 310
    assert s["attempts_count"] == 3
    assert s["best_by_quiz"] == {"a": 150, "b": 60}
    assert s["best_streak"] == 5
    assert abs(s["first_try_accuracy"] - 0.8) < 1e-9


def test_next_steps_picks_weakest_then_not_started():
    mastery = {
        "indexing": {"level": "familiar", "rate": 0.2, "count": 5},
        "metrics": {"level": "proficient", "rate": 0.6, "count": 5},
        "quartiles": {"level": "not_started", "rate": 0.0, "count": 0},
    }
    qoc = {
        "indexing": {"quiz_slug": "journals", "quiz_title_ar": "المجلات"},
        "metrics": {"quiz_slug": "journals", "quiz_title_ar": "المجلات"},
        "quartiles": {"quiz_slug": "journals", "quiz_title_ar": "المجلات"},
    }
    out = next_steps(mastery, qoc, limit=2)
    assert [o["concept"] for o in out] == ["indexing", "metrics"]
    assert out[0]["label_ar"] == CONCEPT_LABELS_AR["indexing"]


def test_next_steps_falls_back_to_not_started_when_few_weak():
    mastery = {
        "indexing": {"level": "familiar", "rate": 0.2, "count": 5},
        "quartiles": {"level": "not_started", "rate": 0.0, "count": 0},
    }
    qoc = {"indexing": {"quiz_slug": "j", "quiz_title_ar": "ج"},
           "quartiles": {"quiz_slug": "j", "quiz_title_ar": "ج"}}
    out = next_steps(mastery, qoc, limit=2)
    assert [o["concept"] for o in out] == ["indexing", "quartiles"]


def test_concept_labels_cover_known_slugs():
    for slug in ("predatory_signs", "indexing", "abstract", "research_gap", "review_types"):
        assert slug in CONCEPT_LABELS_AR
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_progress.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.progress'`.

- [ ] **Step 3: Create `backend/app/progress.py`**

```python
CONCEPT_LABELS_AR = {
    # journals
    "predatory_signs": "علامات المجلات المفترسة",
    "indexing": "الفهرسة",
    "quartiles": "تصنيف الأرباع (Quartiles)",
    "metrics": "مؤشرات التأثير",
    "open_access": "الوصول المفتوح",
    "journal_selection": "اختيار المجلة",
    # foundations
    "methodology_basics": "أساسيات المنهج العلمي",
    "originality": "الأصالة",
    "research_gap": "الفجوة البحثية",
    "gap_types": "أنواع الفجوات البحثية",
    "finding_gaps": "اكتشاف الفجوات",
    # paper-types
    "choosing_type": "اختيار نوع الورقة",
    "original_research": "البحث الأصلي",
    "review_types": "أنواع المراجعات",
    "secondary_research": "البحوث الثانوية (تحليل/مراجعة)",
    "special_formats": "الصيغ الخاصة",
    # paper-parts
    "title": "العنوان",
    "abstract": "الملخص",
    "keywords": "الكلمات المفتاحية",
    "introduction": "المقدمة",
    "methods": "المنهجية",
    "results": "النتائج",
    "discussion": "المناقشة",
    "references": "المراجع",
    "structure": "بنية الورقة",
}


def first_try_of(answer: dict) -> bool:
    return int(answer.get("retries", 0)) == 0 and not answer.get("hint_used")


def level_for(rate: float, count: int) -> str:
    if count == 0:
        return "not_started"
    if rate >= 0.85 and count >= 3:
        return "mastered"
    if rate >= 0.50:
        return "proficient"
    return "familiar"


def mastery_for_concepts(answers: list[dict], recent_n: int = 5) -> dict:
    by_concept: dict[str, list] = {}
    for a in answers:
        by_concept.setdefault(a["concept"], []).append(a)

    result = {}
    for concept, items in by_concept.items():
        recent = sorted(items, key=lambda x: x["order"])[-recent_n:]
        kept = len(recent)
        first_tries = sum(1 for x in recent if first_try_of(x))
        rate = first_tries / kept if kept else 0.0
        result[concept] = {"rate": rate, "count": kept, "level": level_for(rate, kept)}
    return result


def summarize_stats(attempts: list[dict]) -> dict:
    if not attempts:
        return {"total_points": 0, "attempts_count": 0, "best_by_quiz": {},
                "best_streak": 0, "first_try_accuracy": 0.0}
    best_by_quiz: dict[str, int] = {}
    for a in attempts:
        slug = a["quiz_slug"]
        best_by_quiz[slug] = max(best_by_quiz.get(slug, 0), a["total_score"])
    return {
        "total_points": sum(a["total_score"] for a in attempts),
        "attempts_count": len(attempts),
        "best_by_quiz": best_by_quiz,
        "best_streak": max(a.get("max_streak", 0) for a in attempts),
        "first_try_accuracy": round(sum(a["accuracy"] for a in attempts) / len(attempts), 4),
    }


def next_steps(mastery: dict, quiz_of_concept: dict, limit: int = 2) -> list:
    weak = [(c, m) for c, m in mastery.items() if m["level"] in ("familiar", "proficient")]
    weak.sort(key=lambda cm: (cm[1]["rate"], cm[1]["count"]))
    picks = [c for c, _ in weak]
    if len(picks) < limit:
        picks += [c for c, m in mastery.items() if m["level"] == "not_started"]

    out = []
    for concept in picks[:limit]:
        q = quiz_of_concept.get(concept, {})
        out.append({
            "concept": concept,
            "label_ar": CONCEPT_LABELS_AR.get(concept, concept),
            "quiz_slug": q.get("quiz_slug", ""),
            "quiz_title_ar": q.get("quiz_title_ar", ""),
            "level": mastery[concept]["level"],
        })
    return out
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_progress.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/progress.py backend/tests/test_progress.py
git commit -m "feat: mastery/stats/next-step engine for learner dashboard"
```

---

### Task 2: Contestant data queries — `app/models.py`

**Files:**
- Modify: `backend/app/models.py` (append functions; add `import json` is already present at top)
- Create: `backend/tests/test_models_dashboard.py`

**Interfaces:**
- Consumes: existing tables `answers, attempts, questions, quizzes`.
- Produces:
  - `get_contestant_answers(conn, contestant_id) -> list[dict]` — finished attempts only; each
    dict `{concept, retries, hint_used, quiz_slug, order}` where `concept` is read from the
    question's `data_json`, and `order` ranks ascending by `(attempts.finished_at, answers.id)`.
  - `get_contestant_attempts(conn, contestant_id) -> list[dict]` — finished attempts newest
    first; each `{quiz_slug, quiz_title_ar, total_score, accuracy, max_streak, finished_at}`.
  - `quiz_of_concept(conn) -> dict[str, dict]` — `{concept: {quiz_slug, quiz_title_ar}}`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_models_dashboard.py`

```python
from app.models import (
    upsert_contestant, create_attempt, finish_attempt, record_answer,
    get_questions, get_contestant_answers, get_contestant_attempts, quiz_of_concept,
)
from app.seed import seed_quiz


DOC = {
    "slug": "journals", "title_ar": "المجلات", "pdf_filename": "x.pdf",
    "questions": [
        {"type": "tf", "prompt_ar": "س1", "options_ar": ["صح", "خطأ"], "correct_index": 0, "concept": "indexing"},
        {"type": "tf", "prompt_ar": "س2", "options_ar": ["صح", "خطأ"], "correct_index": 0, "concept": "metrics"},
    ],
}


def _setup(conn):
    quiz_id = seed_quiz(conn, DOC)
    qs = get_questions(conn, quiz_id)
    uid = upsert_contestant(conn, {"id": 1, "first_name": "A"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-27T10:00:00")
    record_answer(conn, aid, qs[0]["id"], {}, True, 0, 100, retries=0, hint_used=0)
    record_answer(conn, aid, qs[1]["id"], {}, True, 0, 80, retries=2, hint_used=1)
    finish_attempt(conn, aid, 180, 0.5, 1000, "2026-06-27T10:00:10")
    return uid, quiz_id


def test_get_contestant_answers_has_concept_and_order(conn):
    uid, _ = _setup(conn)
    rows = get_contestant_answers(conn, uid)
    assert len(rows) == 2
    concepts = {r["concept"] for r in rows}
    assert concepts == {"indexing", "metrics"}
    assert all("order" in r and "retries" in r and "hint_used" in r for r in rows)
    # order is strictly increasing in insertion order
    assert rows[0]["order"] < rows[1]["order"]


def test_get_contestant_answers_only_finished(conn):
    uid, quiz_id = _setup(conn)
    # an unfinished attempt's answers must be excluded
    from app.models import get_questions
    qs = get_questions(conn, quiz_id)
    aid2 = create_attempt(conn, uid, quiz_id, "async", "2026-06-27T11:00:00")
    record_answer(conn, aid2, qs[0]["id"], {}, True, 0, 100, retries=0, hint_used=0)
    rows = get_contestant_answers(conn, uid)
    assert len(rows) == 2  # still only the finished attempt's answers


def test_get_contestant_attempts(conn):
    uid, _ = _setup(conn)
    rows = get_contestant_attempts(conn, uid)
    assert len(rows) == 1
    assert rows[0]["quiz_title_ar"] == "المجلات"
    assert rows[0]["total_score"] == 180
    assert rows[0]["max_streak"] == 0  # not set in this attempt


def test_quiz_of_concept(conn):
    _setup(conn)
    qoc = quiz_of_concept(conn)
    assert qoc["indexing"]["quiz_slug"] == "journals"
    assert qoc["metrics"]["quiz_title_ar"] == "المجلات"
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_models_dashboard.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_contestant_answers'`.

- [ ] **Step 3: Append to `backend/app/models.py`** (after `leaderboard_overall`)

```python
def get_contestant_answers(conn, contestant_id):
    rows = conn.execute(
        """
        SELECT q.data_json AS data_json, ans.retries AS retries, ans.hint_used AS hint_used,
               qz.slug AS quiz_slug
        FROM answers ans
        JOIN attempts a ON a.id = ans.attempt_id
        JOIN questions q ON q.id = ans.question_id
        JOIN quizzes qz ON qz.id = q.quiz_id
        WHERE a.contestant_id = ? AND a.finished_at IS NOT NULL
        ORDER BY a.finished_at ASC, ans.id ASC
        """,
        (contestant_id,),
    ).fetchall()
    out = []
    for order, r in enumerate(rows):
        concept = json.loads(r["data_json"]).get("concept", "")
        out.append({
            "concept": concept,
            "retries": r["retries"],
            "hint_used": r["hint_used"],
            "quiz_slug": r["quiz_slug"],
            "order": order,
        })
    return out


def get_contestant_attempts(conn, contestant_id):
    rows = conn.execute(
        """
        SELECT qz.slug AS quiz_slug, qz.title_ar AS quiz_title_ar,
               a.total_score AS total_score, a.accuracy AS accuracy,
               a.max_streak AS max_streak, a.finished_at AS finished_at
        FROM attempts a
        JOIN quizzes qz ON qz.id = a.quiz_id
        WHERE a.contestant_id = ? AND a.finished_at IS NOT NULL
        ORDER BY a.finished_at DESC
        """,
        (contestant_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def quiz_of_concept(conn):
    rows = conn.execute(
        """SELECT q.data_json AS data_json, qz.slug AS quiz_slug, qz.title_ar AS quiz_title_ar
           FROM questions q JOIN quizzes qz ON qz.id = q.quiz_id"""
    ).fetchall()
    mapping = {}
    for r in rows:
        concept = json.loads(r["data_json"]).get("concept", "")
        if concept and concept not in mapping:
            mapping[concept] = {"quiz_slug": r["quiz_slug"], "quiz_title_ar": r["quiz_title_ar"]}
    return mapping
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_models_dashboard.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models_dashboard.py
git commit -m "feat: contestant answer/attempt queries for dashboard"
```

---

### Task 3: Dashboard endpoint — `GET /api/me/dashboard`

**Files:**
- Modify: `backend/app/api.py` (add the route; `import` `progress`)
- Modify: `backend/tests/test_api.py` (add dashboard tests)

**Interfaces:**
- Consumes: `app.progress`, `app.models.get_contestant_answers/get_contestant_attempts/quiz_of_concept`, `app.badges.get_badges`, `app.auth.validate_init_data`.
- Produces: `GET /api/me/dashboard` (header `X-Init-Data`) →
  `{stats:{...,hints_used}, mastery:[{concept,label_ar,quiz_slug,quiz_title_ar,level,rate,count}], history:[...max 15], next:[...], badges:[...]}`. 401 without valid initData.

- [ ] **Step 1: Add the failing tests** to `backend/tests/test_api.py` (append; reuses `api_client` + `_init_data` already in the file)

```python
def test_dashboard_requires_initdata(api_client):
    assert api_client.get("/api/me/dashboard", headers={"X-Init-Data": "bad&hash=x"}).status_code == 401


def test_dashboard_shape_after_attempt(api_client, monkeypatch):
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    init = _init_data({"id": 555, "first_name": "Maya"})
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    # answer the 2 SAMPLE_DOC questions first-try
    answers = [{"question_id": q["id"], "retries": 0, "hint_used": False} for q in qs]
    api_client.post("/api/quizzes/journals/submit", headers={"X-Init-Data": init},
                    json={"answers": answers, "duration_ms": 1000})

    dash = api_client.get("/api/me/dashboard", headers={"X-Init-Data": init}).json()
    assert set(dash) == {"stats", "mastery", "history", "next", "badges"}
    assert dash["stats"]["attempts_count"] == 1
    assert dash["stats"]["hints_used"] == 0
    # every concept of the seeded quiz appears (answered + not), each with a level + label
    assert all({"concept", "label_ar", "level"} <= set(m) for m in dash["mastery"])
    assert len(dash["history"]) == 1
    assert dash["history"][0]["quiz_slug"] == "journals"
```

Note: `SAMPLE_DOC` has 2 questions both `concept = "predatory_signs"`; sampling returns ≤10 so both come back.

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_api.py -k dashboard -v`
Expected: FAIL — route returns 404 (not defined).

- [ ] **Step 3: Edit `backend/app/api.py`** — add `from app import ... progress` to the existing top import of app modules, i.e. change

```python
from app import models, badges, notify
```
to
```python
from app import models, badges, notify, progress
```

Then add the route (place after the `me_badges` route, before `_now`):

```python
@router.get("/me/dashboard")
def me_dashboard(request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    uid = int(user["id"])

    answers = models.get_contestant_answers(conn, uid)
    attempts = models.get_contestant_attempts(conn, uid)
    qoc = models.quiz_of_concept(conn)

    raw_mastery = progress.mastery_for_concepts(answers)
    full_mastery = {}
    mastery_list = []
    for concept, q in qoc.items():
        m = raw_mastery.get(concept, {"rate": 0.0, "count": 0, "level": "not_started"})
        full_mastery[concept] = m
        mastery_list.append({
            "concept": concept,
            "label_ar": progress.CONCEPT_LABELS_AR.get(concept, concept),
            "quiz_slug": q["quiz_slug"],
            "quiz_title_ar": q["quiz_title_ar"],
            "level": m["level"],
            "rate": round(m["rate"], 2),
            "count": m["count"],
        })

    stats = progress.summarize_stats(attempts)
    stats["hints_used"] = sum(1 for a in answers if a["hint_used"])

    return {
        "stats": stats,
        "mastery": mastery_list,
        "history": attempts[:15],
        "next": progress.next_steps(full_mastery, qoc),
        "badges": badges.get_badges(conn, uid),
    }
```

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd backend && pytest tests/test_api.py -k dashboard -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api.py backend/tests/test_api.py
git commit -m "feat: GET /api/me/dashboard aggregating mastery/stats/history/next"
```

---

### Task 4: Frontend — `screen-progress`

**Files:**
- Modify: `frontend/index.html` (add a home button + the progress screen)
- Modify: `frontend/app.js` (LEVELS map, `loadDashboard()`, wire button, register screen)
- Modify: `frontend/styles.css` (mastery chip + dashboard styles)

**Interfaces:**
- Consumes: `GET /api/me/dashboard` with `X-Init-Data: Telegram.WebApp.initData`.
- No automated tests (UI); verified by the deploy smoke check + manual Telegram playthrough.

- [ ] **Step 1: Edit `frontend/index.html`** — add a progress button to `screen-home` (after the badges button) and a new screen (after `screen-badges`).

In `screen-home`, after the `btn-my-badges` button:
```html
      <button id="btn-my-progress" class="quiz-card">📊 تقدّمي</button>
```

After the `screen-badges` section:
```html
    <section id="screen-progress" class="screen hidden">
      <h2>تقدّمي 📊</h2>
      <div id="dash-stats" class="dash-stats"></div>
      <div id="dash-next" class="dash-next"></div>
      <h3>إتقان المفاهيم</h3>
      <div id="dash-mastery"></div>
      <h3>آخر المحاولات</h3>
      <ol id="dash-history" class="dash-history"></ol>
      <button id="btn-progress-home">العودة</button>
    </section>
```

- [ ] **Step 2: Edit `frontend/app.js`** — register the screen and wire the button.

Change the `screens` array (line ~4) to include `"progress"`:
```javascript
const screens = ["home", "runner", "report", "board", "badges", "funfact", "progress"];
```

In `loadHome()`, after the `btn-my-badges` wiring line, add:
```javascript
  document.getElementById("btn-my-progress").onclick = loadDashboard;
```

Add the level metadata and `loadDashboard()` (place near `loadBadges`):
```javascript
const LEVELS = {
  not_started: { ar: "لم يبدأ", cls: "lv-none" },
  familiar: { ar: "مبتدئ", cls: "lv-familiar" },
  proficient: { ar: "جيد", cls: "lv-proficient" },
  mastered: { ar: "متقن", cls: "lv-mastered" },
};

async function loadDashboard() {
  let dash;
  try {
    dash = await api("/me/dashboard", { headers: { "X-Init-Data": tg.initData } });
  } catch (e) {
    document.getElementById("dash-stats").textContent = "تعذّر تحميل التقدّم";
    show("progress");
    return;
  }

  const s = dash.stats;
  document.getElementById("dash-stats").innerHTML =
    `<div class="stat"><b>${s.total_points}</b><span>نقطة</span></div>` +
    `<div class="stat"><b>${s.attempts_count}</b><span>محاولة</span></div>` +
    `<div class="stat"><b>${Math.round(s.first_try_accuracy * 100)}%</b><span>دقة أول محاولة</span></div>` +
    `<div class="stat"><b>${s.best_streak}</b><span>أطول سلسلة</span></div>`;

  const nextBox = document.getElementById("dash-next");
  nextBox.innerHTML = "";
  if (dash.next && dash.next.length) {
    const head = document.createElement("div");
    head.className = "next-head";
    head.textContent = "ما التالي؟";
    nextBox.appendChild(head);
    dash.next.forEach((n) => {
      const b = document.createElement("button");
      b.className = "next-card";
      b.innerHTML = `راجع <b>${n.label_ar}</b> في «${n.quiz_title_ar}»`;
      b.onclick = () => startQuiz(n.quiz_slug);
      nextBox.appendChild(b);
    });
  }

  // mastery grouped by quiz
  const mBox = document.getElementById("dash-mastery");
  mBox.innerHTML = "";
  const byQuiz = {};
  dash.mastery.forEach((m) => { (byQuiz[m.quiz_title_ar] = byQuiz[m.quiz_title_ar] || []).push(m); });
  Object.keys(byQuiz).forEach((title) => {
    const group = document.createElement("div");
    group.className = "mastery-group";
    group.innerHTML = `<div class="mastery-title">${title}</div>`;
    const chips = document.createElement("div");
    chips.className = "mastery-chips";
    byQuiz[title].forEach((m) => {
      const lv = LEVELS[m.level] || LEVELS.not_started;
      const chip = document.createElement("span");
      chip.className = "mchip " + lv.cls;
      chip.innerHTML = `${m.label_ar}<small>${lv.ar}</small>`;
      chips.appendChild(chip);
    });
    group.appendChild(chips);
    mBox.appendChild(group);
  });

  const hist = document.getElementById("dash-history");
  hist.innerHTML = "";
  dash.history.forEach((h) => {
    const li = document.createElement("li");
    const when = (h.finished_at || "").slice(0, 10);
    li.innerHTML = `${h.quiz_title_ar} — ${h.total_score} نقطة · ${Math.round(h.accuracy * 100)}% <small>${when}</small>`;
    hist.appendChild(li);
  });

  document.getElementById("btn-progress-home").onclick = loadHome;
  show("progress");
}
```

- [ ] **Step 3: Edit `frontend/styles.css`** — append dashboard styles.

```css
.dash-stats { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 8px 0; }
.dash-stats .stat { background: var(--card); border-radius: 12px; padding: 10px 14px; text-align: center; min-width: 70px; }
.dash-stats .stat b { display: block; font-size: 1.4rem; }
.dash-stats .stat span { font-size: .75rem; color: #9aa4bf; }
.dash-next { margin: 10px 0; }
.next-head { font-weight: 600; margin-bottom: 6px; }
.next-card { display: block; width: 100%; text-align: right; background: var(--accent); border: none;
  border-radius: 12px; padding: 12px; margin: 6px 0; color: #fff; cursor: pointer; }
.mastery-group { margin: 10px 0; }
.mastery-title { font-weight: 600; margin-bottom: 6px; }
.mastery-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.mchip { border-radius: 999px; padding: 6px 10px; font-size: .85rem; color: #10131a; display: flex; gap: 6px; align-items: center; }
.mchip small { font-size: .65rem; opacity: .8; }
.lv-none { background: #3a4255; color: #c8d0e0; }
.lv-familiar { background: #e0a64f; }
.lv-proficient { background: #4f8cff; color: #fff; }
.lv-mastered { background: #2fbf71; color: #fff; }
.dash-history { list-style: none; padding: 0; }
.dash-history li { background: var(--card); border-radius: 10px; padding: 10px; margin: 6px 0; }
.dash-history small { color: #9aa4bf; }
```

- [ ] **Step 4: Manual smoke test in a browser**

Run: `cd backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --reload --port 8000`
Open `http://localhost:8000/app/`, click **📊 تقدّمي**. Expected: the progress screen renders (stats row, "ما التالي؟" card, concept mastery chips grouped by quiz, recent-attempts list). Outside Telegram `initData` is empty so the request 401s and the screen shows "تعذّر تحميل التقدّم" — full data is verified in Telegram during deploy.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat: تقدّمي learner dashboard screen (mastery, stats, history, next)"
```

---

## Deployment note (after all tasks)
No DB migration and **no reseed** — Phase 3C only reads existing data. Deploy = rebuild → `up`.
The frontend asset version auto-busts (main.py stamps `app.js`/`styles.css` with the bundle hash),
so the new dashboard reaches clients without a manual `?v=` bump.

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Concept mastery map (first-try, recent-5, 4 levels) → Task 1 (`level_for`, `mastery_for_concepts`). ✓
- Progress & stats → Task 1 (`summarize_stats`) + Task 3 (`hints_used` from answers). ✓
- Activity history → Task 2 (`get_contestant_attempts`) + Task 3 (capped 15) + Task 4 list. ✓
- What-to-do-next → Task 1 (`next_steps`) + Task 4 nudge cards. ✓
- Server-side aggregation, `/me/dashboard` auth via initData → Task 3. ✓
- Concept labels in code → Task 1 `CONCEPT_LABELS_AR`. ✓
- Every concept incl. not_started → Task 3 merges `quiz_of_concept` with mastery. ✓
- New Mini App screen from a home button → Task 4. ✓
- No DB migration; concept read from data_json in Python → Task 2. ✓

**Placeholder scan:** No "TBD/handle edge cases" in code steps; every step carries full code.

**Type consistency:** `mastery_for_concepts`/`level_for`/`summarize_stats`/`next_steps` signatures
match between Task 1 (defined) and Task 3 (called). Answer dict keys (`concept, retries,
hint_used, order`) produced by Task 2 match what Task 1 consumes. `next_steps` consumes the full
mastery dict `{concept: {level, rate, count}}` that Task 3 builds (`full_mastery`). The frontend
`LEVELS` keys match the four level strings from Task 1.

## Out of scope (future)
- Materialized mastery, charts/time-series, decay weighting beyond recent-N.
- Cross-learner comparison; bot-side dashboard; concept labels in content JSON.
