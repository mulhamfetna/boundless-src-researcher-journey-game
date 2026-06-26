# Phase 2A — Game Mechanics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add match/order question types (drag-and-drop), partial-credit scoring, 4 badges, an overall leaderboard, and auto-DM of the report — all on the existing live `journals` quiz.

**Architecture:** Extends the Phase 1 stack (FastAPI + stdlib `sqlite3` + vanilla RTL Mini App + python-telegram-bot). New pure modules (`badges.py`, `notify.py`) and additions to `scoring.py`, `content_schema.py`, `models.py`, `report.py`, `seed.py`, `api.py`. A one-time `migrate.py` widens the live DB. The Mini App gains pointer-event drag renderers and a badges screen.

**Tech Stack:** Python 3.14, FastAPI, stdlib `sqlite3`, `httpx` (already a dep), pytest; dependency-free HTML/CSS/JS using Pointer Events.

## Global Constraints

- **Build on Phase 1; do not rewrite it.** Reuse existing functions; keep their signatures unless a task says otherwise.
- **Language:** all learner-facing strings are **Arabic, RTL**.
- **Question types:** add `match` and `order`. Payloads live in the existing `questions.data_json` text column.
- **Partial credit:** `match` = correct_pairs / total_pairs; `order` = correctly-placed / n. **Streak and accuracy advance only when the answer is 100% (`is_full`).**
- **Scoring is server-authoritative.** Client submits answers + `time_ms`; never a score. `time_ms` clamped to `[0, 60000]`.
- **Score formula:** `round((base_points + speed_bonus(time_ms)) * fraction * streak_multiplier(streak_before))`.
- **Badges:** exactly `perfect_quiz`, `speed_demon`, `streak_master`, `first_finish`. Awarded once (DB `UNIQUE(contestant_id, code)`).
- **`speed_demon` threshold:** average per-answer speed bonus `>= 35` (of max 50).
- **Auto-DM:** the backend (`web`) posts `sendMessage`; **fire-and-forget**, never raises, disabled when `BOT_TOKEN` is empty.
- **Overall leaderboard:** sum of each contestant's best score per quiz.
- **Identity:** every data-recording call validates Telegram `initData` HMAC.
- **Tests never call real Telegram** and never need a real token.
- **Package root:** backend code under `backend/app/`, imported as `app.<module>`; tests run from `backend/` with `pytest`.
- **Commit after every task.**

## Answer & payload shapes (single source of truth)

Stored `data_json` by type:
- `mcq` / `tf` / `image`: `{"options_ar": [...], "correct_index": int}` (unchanged)
- `match`: `{"left_ar": [...], "right_ar": [...], "correct_pairs": [[left_idx, right_idx], ...]}`
- `order`: `{"items_ar": [...], "correct_sequence": [orig_idx, ...]}`

Client answer object inside `submit` `payload["answers"]`:
- `mcq`/`tf`/`image`: `{"question_id", "index", "time_ms"}`
- `match`: `{"question_id", "pairs": [[left_idx, right_idx], ...], "time_ms"}`
- `order`: `{"question_id", "sequence": [orig_idx, ...], "time_ms"}`

`GET /questions` exposes per type (NO answer keys): `options_ar` (mcq/tf/image), `left_ar`+`right_ar` (match), `items_ar` (order).

---

### Task 1: Schema migration — drop type CHECK, add `max_streak`, badges UNIQUE

**Files:**
- Modify: `backend/app/db.py` (the `SCHEMA` string, for fresh installs)
- Create: `backend/app/migrate.py`, `backend/tests/test_migrate.py`

**Interfaces:**
- Consumes: `app.db.connect`, `app.db.init_schema`.
- Produces: `app.migrate.migrate(conn) -> list[str]` — applies needed changes, returns the list of changes made (empty if already current). `python -m app.migrate` runs it against `QUIZ_DB_PATH`.

- [ ] **Step 1: Update `SCHEMA` in `backend/app/db.py`** so fresh DBs are already correct. Replace the `questions` `type` line, the `attempts` table, and the `badges` table with:

In `questions` table, change:
```
    type          TEXT NOT NULL CHECK (type IN ('mcq','tf','image')),
```
to:
```
    type          TEXT NOT NULL,
```

In `attempts` table, add `max_streak` after `duration_ms`:
```
    duration_ms      INTEGER NOT NULL DEFAULT 0,
    max_streak       INTEGER NOT NULL DEFAULT 0,
```

Replace the `badges` table with:
```
CREATE TABLE IF NOT EXISTS badges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    contestant_id INTEGER NOT NULL REFERENCES contestants(telegram_user_id),
    code          TEXT NOT NULL,
    earned_at     TEXT NOT NULL,
    UNIQUE(contestant_id, code)
);
```

- [ ] **Step 2: Write the failing test** `backend/tests/test_migrate.py`

```python
import sqlite3
from app.db import connect
from app.migrate import migrate

# Build an OLD-schema DB (Phase 1 shape) to migrate from.
OLD_SCHEMA = """
CREATE TABLE quizzes (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL,
    title_ar TEXT NOT NULL, pdf_filename TEXT NOT NULL, display_order INTEGER NOT NULL DEFAULT 0);
CREATE TABLE questions (id INTEGER PRIMARY KEY AUTOINCREMENT, quiz_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('mcq','tf','image')), prompt_ar TEXT NOT NULL,
    base_points INTEGER NOT NULL DEFAULT 100, explanation_ar TEXT NOT NULL DEFAULT '',
    source_page INTEGER, data_json TEXT NOT NULL, display_order INTEGER NOT NULL DEFAULT 0);
CREATE TABLE contestants (telegram_user_id INTEGER PRIMARY KEY, first_name TEXT NOT NULL DEFAULT '',
    username TEXT, created_at TEXT NOT NULL);
CREATE TABLE attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, contestant_id INTEGER NOT NULL,
    quiz_id INTEGER NOT NULL, mode TEXT NOT NULL DEFAULT 'async', total_score INTEGER NOT NULL DEFAULT 0,
    accuracy REAL NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0, started_at TEXT, finished_at TEXT);
CREATE TABLE answers (id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL, given_json TEXT NOT NULL, is_correct INTEGER NOT NULL,
    time_ms INTEGER NOT NULL, points_awarded INTEGER NOT NULL);
CREATE TABLE badges (id INTEGER PRIMARY KEY AUTOINCREMENT, contestant_id INTEGER NOT NULL,
    code TEXT NOT NULL, earned_at TEXT NOT NULL);
"""


def _old_db(path):
    conn = connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.execute("INSERT INTO quizzes (slug,title_ar,pdf_filename) VALUES ('j','t','f.pdf')")
    conn.execute("INSERT INTO questions (quiz_id,type,prompt_ar,data_json) VALUES (1,'mcq','p','{}')")
    conn.commit()
    return conn


def test_migrate_adds_max_streak_and_drops_check(tmp_path):
    conn = _old_db(str(tmp_path / "old.db"))
    changes = migrate(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(attempts)")}
    assert "max_streak" in cols
    # CHECK is gone: an 'order' type now inserts without error
    conn.execute("INSERT INTO questions (quiz_id,type,prompt_ar,data_json) VALUES (1,'order','p','{}')")
    conn.commit()
    assert changes  # non-empty on first run


def test_migrate_preserves_rows_and_ids(tmp_path):
    conn = _old_db(str(tmp_path / "old.db"))
    migrate(conn)
    rows = conn.execute("SELECT id, type FROM questions ORDER BY id").fetchall()
    assert rows[0]["id"] == 1 and rows[0]["type"] == "mcq"


def test_migrate_idempotent(tmp_path):
    conn = _old_db(str(tmp_path / "old.db"))
    migrate(conn)
    second = migrate(conn)
    assert second == []  # nothing left to do


def test_migrate_badges_unique(tmp_path):
    conn = _old_db(str(tmp_path / "old.db"))
    migrate(conn)
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.execute("INSERT OR IGNORE INTO badges (contestant_id, code, earned_at) VALUES (1,'x',datetime('now'))")
    conn.execute("INSERT OR IGNORE INTO badges (contestant_id, code, earned_at) VALUES (1,'x',datetime('now'))")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM badges").fetchone()[0] == 1
```

- [ ] **Step 3: Run it, expect failure**

Run: `cd backend && pytest tests/test_migrate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.migrate'`.

- [ ] **Step 4: Create `backend/app/migrate.py`**

```python
"""One-time, idempotent migrations for the Phase 2A schema changes.

Run against a live DB: `QUIZ_DB_PATH=/data/quiz.db python -m app.migrate`.
SQLite cannot drop a CHECK constraint in place, so `questions` is rebuilt with
the standard table-rebuild pattern (FKs off, copy, drop, rename), preserving ids.
"""
import sqlite3

from app.config import settings
from app.db import connect


def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _questions_has_check(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='questions'"
    ).fetchone()
    return bool(row) and "CHECK" in (row["sql"] or "")


def migrate(conn: sqlite3.Connection) -> list[str]:
    changes: list[str] = []

    if "max_streak" not in _columns(conn, "attempts"):
        conn.execute("ALTER TABLE attempts ADD COLUMN max_streak INTEGER NOT NULL DEFAULT 0")
        changes.append("attempts.max_streak")

    if _questions_has_check(conn):
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript(
            """
            CREATE TABLE questions__new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
                type TEXT NOT NULL,
                prompt_ar TEXT NOT NULL,
                base_points INTEGER NOT NULL DEFAULT 100,
                explanation_ar TEXT NOT NULL DEFAULT '',
                source_page INTEGER,
                data_json TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO questions__new
                SELECT id, quiz_id, type, prompt_ar, base_points, explanation_ar,
                       source_page, data_json, display_order FROM questions;
            DROP TABLE questions;
            ALTER TABLE questions__new RENAME TO questions;
            """
        )
        conn.execute("PRAGMA foreign_keys=ON")
        changes.append("questions.drop_check")

    # Ensure UNIQUE(contestant_id, code) on badges.
    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='badges'"
    ).fetchall()
    has_unique = any("contestant" in (r["name"] or "") for r in idx)
    if not has_unique:
        # de-dup any existing rows first, then add the unique index
        conn.executescript(
            """
            DELETE FROM badges WHERE id NOT IN
                (SELECT MIN(id) FROM badges GROUP BY contestant_id, code);
            CREATE UNIQUE INDEX IF NOT EXISTS ux_badges_contestant_code
                ON badges (contestant_id, code);
            """
        )
        changes.append("badges.unique")

    conn.commit()
    return changes


def main():
    conn = connect(settings.db_path)
    changes = migrate(conn)
    print("migrated:", changes or "already current")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests, expect pass**

Run: `cd backend && pytest tests/test_migrate.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Run the full suite** (the `db.py` SCHEMA change must not break Phase 1 tests)

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db.py backend/app/migrate.py backend/tests/test_migrate.py
git commit -m "feat: schema migration for match/order, max_streak, badges unique"
```

---

### Task 2: Scoring — `grade()` and `score_fraction()`

**Files:**
- Modify: `backend/app/scoring.py`
- Modify: `backend/tests/test_scoring.py` (append)

**Interfaces:**
- Consumes: existing `speed_bonus`, `streak_multiplier`, `clamp_time`, `score_answer` (keep unchanged).
- Produces:
  - `app.scoring.grade(qtype: str, data: dict, given: dict) -> tuple[float, bool]` → `(fraction, is_full)`.
  - `app.scoring.score_fraction(base_points: int, fraction: float, time_ms: int, streak_before: int) -> int` → `round((base_points + speed_bonus(time_ms)) * fraction * streak_multiplier(streak_before))`.

- [ ] **Step 1: Append failing tests** to `backend/tests/test_scoring.py`

```python
from app.scoring import grade, score_fraction


def test_grade_mcq_full_and_zero():
    data = {"options_ar": ["a", "b"], "correct_index": 1}
    assert grade("mcq", data, {"index": 1}) == (1.0, True)
    assert grade("mcq", data, {"index": 0}) == (0.0, False)


def test_grade_match_partial():
    data = {"left_ar": ["L0", "L1"], "right_ar": ["R0", "R1"],
            "correct_pairs": [[0, 1], [1, 0]]}
    # one of two pairs right
    frac, full = grade("match", data, {"pairs": [[0, 1], [1, 1]]})
    assert frac == 0.5 and full is False
    frac, full = grade("match", data, {"pairs": [[0, 1], [1, 0]]})
    assert frac == 1.0 and full is True


def test_grade_order_partial():
    data = {"items_ar": ["A", "B", "C"], "correct_sequence": [2, 0, 1]}
    # positions: [2,0,1] correct -> 3/3
    assert grade("order", data, {"sequence": [2, 0, 1]}) == (1.0, True)
    # [2,1,0] -> only position 0 correct -> 1/3
    frac, full = grade("order", data, {"sequence": [2, 1, 0]})
    assert round(frac, 3) == 0.333 and full is False


def test_grade_handles_missing_or_malformed():
    data = {"items_ar": ["A", "B"], "correct_sequence": [0, 1]}
    assert grade("order", data, {}) == (0.0, False)
    data2 = {"left_ar": ["L"], "right_ar": ["R"], "correct_pairs": [[0, 0]]}
    assert grade("match", data2, {"pairs": []}) == (0.0, False)


def test_score_fraction_partial():
    # base 100 + bonus 0 (slow), fraction 0.5, streak 0 -> 50
    assert score_fraction(100, 0.5, 90000, 0) == 50
    # base 100 + bonus 50 (fast), fraction 1.0, streak 0 -> 150
    assert score_fraction(100, 1.0, 0, 0) == 150
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_scoring.py -k "grade or score_fraction" -v`
Expected: FAIL — `ImportError: cannot import name 'grade'`.

- [ ] **Step 3: Append to `backend/app/scoring.py`**

```python
def score_fraction(base_points: int, fraction: float, time_ms: int, streak_before: int) -> int:
    if fraction <= 0:
        return 0
    raw = (base_points + speed_bonus(time_ms)) * fraction * streak_multiplier(streak_before)
    return round(raw)


def grade(qtype: str, data: dict, given: dict) -> tuple[float, bool]:
    if qtype in ("mcq", "tf", "image"):
        ok = given.get("index") is not None and int(given["index"]) == data["correct_index"]
        return (1.0, True) if ok else (0.0, False)

    if qtype == "match":
        correct = {tuple(p) for p in data["correct_pairs"]}
        given_pairs = {tuple(p) for p in given.get("pairs", [])}
        if not correct:
            return (0.0, False)
        frac = len(given_pairs & correct) / len(correct)
        return (frac, frac == 1.0)

    if qtype == "order":
        seq = data["correct_sequence"]
        given_seq = given.get("sequence", [])
        if len(given_seq) != len(seq) or not seq:
            return (0.0, False)
        placed = sum(1 for i, v in enumerate(seq) if i < len(given_seq) and given_seq[i] == v)
        frac = placed / len(seq)
        return (frac, frac == 1.0)

    return (0.0, False)
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_scoring.py -v`
Expected: PASS (all, including the Phase 1 scoring tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/scoring.py backend/tests/test_scoring.py
git commit -m "feat: grade() and partial-credit score_fraction()"
```

---

### Task 3: Content schema — validate `match` and `order`

**Files:**
- Modify: `backend/app/content_schema.py`
- Modify: `backend/tests/test_content_schema.py` (append)

**Interfaces:**
- Produces: `validate_quiz` additionally accepts `match`/`order` questions and validates their shapes.

- [ ] **Step 1: Append failing tests** to `backend/tests/test_content_schema.py`

```python
def test_valid_match_passes():
    doc = _good_doc()
    doc["questions"].append({
        "type": "match", "prompt_ar": "طابق",
        "left_ar": ["L0", "L1"], "right_ar": ["R0", "R1"],
        "correct_pairs": [[0, 1], [1, 0]],
    })
    validate_quiz(doc)


def test_valid_order_passes():
    doc = _good_doc()
    doc["questions"].append({
        "type": "order", "prompt_ar": "رتّب",
        "items_ar": ["A", "B", "C"], "correct_sequence": [2, 0, 1],
    })
    validate_quiz(doc)


def test_match_pair_index_out_of_range_fails():
    doc = _good_doc()
    doc["questions"].append({
        "type": "match", "prompt_ar": "طابق",
        "left_ar": ["L0"], "right_ar": ["R0"], "correct_pairs": [[0, 5]],
    })
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_order_sequence_not_permutation_fails():
    doc = _good_doc()
    doc["questions"].append({
        "type": "order", "prompt_ar": "رتّب",
        "items_ar": ["A", "B"], "correct_sequence": [0, 0],
    })
    with pytest.raises(SchemaError):
        validate_quiz(doc)
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_content_schema.py -k "match or order" -v`
Expected: FAIL — `match`/`order` rejected as bad type.

- [ ] **Step 3: Edit `backend/app/content_schema.py`**

Change the types set:
```python
VALID_TYPES = {"mcq", "tf", "image", "match", "order"}
```

In `validate_quiz`, the existing loop validates `options_ar`/`correct_index` for every question — that must now apply ONLY to the option types. Wrap the existing option checks and add the new ones. Replace the body of the `for i, q in enumerate(...)` loop with:

```python
    for i, q in enumerate(doc["questions"]):
        where = f"question[{i}]"
        _require(q.get("type") in VALID_TYPES, f"{where}: bad type {q.get('type')!r}")
        _require(bool(q.get("prompt_ar")), f"{where}: empty prompt_ar")

        if q["type"] in ("mcq", "tf", "image"):
            options = q.get("options_ar")
            _require(isinstance(options, list), f"{where}: options_ar must be a list")
            if q["type"] == "tf":
                _require(len(options) == 2, f"{where}: tf needs exactly 2 options")
            else:
                _require(len(options) >= 2, f"{where}: needs >= 2 options")
            ci = q.get("correct_index")
            _require(isinstance(ci, int) and 0 <= ci < len(options), f"{where}: correct_index out of range")
            if q["type"] == "image":
                _require("asset" in q, f"{where}: image question needs an asset")

        elif q["type"] == "match":
            left, right = q.get("left_ar"), q.get("right_ar")
            _require(isinstance(left, list) and left, f"{where}: left_ar must be non-empty list")
            _require(isinstance(right, list) and right, f"{where}: right_ar must be non-empty list")
            pairs = q.get("correct_pairs")
            _require(isinstance(pairs, list) and pairs, f"{where}: correct_pairs must be non-empty list")
            seen_left = set()
            for p in pairs:
                _require(isinstance(p, list) and len(p) == 2, f"{where}: each pair is [left_idx, right_idx]")
                li, ri = p
                _require(0 <= li < len(left), f"{where}: left index out of range")
                _require(0 <= ri < len(right), f"{where}: right index out of range")
                _require(li not in seen_left, f"{where}: left item {li} matched twice")
                seen_left.add(li)

        elif q["type"] == "order":
            items = q.get("items_ar")
            _require(isinstance(items, list) and len(items) >= 2, f"{where}: items_ar needs >= 2 items")
            seq = q.get("correct_sequence")
            _require(isinstance(seq, list) and sorted(seq) == list(range(len(items))),
                     f"{where}: correct_sequence must be a permutation of range(len(items_ar))")

        if "asset" in q:
            a = q["asset"]
            _require(bool(a.get("file")), f"{where}: asset.file required")
            _require(bool(a.get("source_url")), f"{where}: asset.source_url required")
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_content_schema.py -v`
Expected: PASS (all, including Phase 1 schema tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/content_schema.py backend/tests/test_content_schema.py
git commit -m "feat: validate match/order question shapes"
```

---

### Task 4: Seed loader — store `match`/`order` payloads

**Files:**
- Modify: `backend/app/seed.py`
- Modify: `backend/tests/test_seed.py` (append)

**Interfaces:**
- Consumes: `validate_quiz`.
- Produces: `seed_quiz` writes the correct `data_json` per type (per "Answer & payload shapes").

- [ ] **Step 1: Append failing test** to `backend/tests/test_seed.py`

```python
import json as _json
from app.models import get_questions, get_quiz_by_slug


def test_seed_stores_match_and_order_payloads(conn):
    doc = {
        "slug": "mix", "title_ar": "t", "pdf_filename": "f.pdf",
        "questions": [
            {"type": "match", "prompt_ar": "طابق", "left_ar": ["L0", "L1"],
             "right_ar": ["R0", "R1"], "correct_pairs": [[0, 1], [1, 0]]},
            {"type": "order", "prompt_ar": "رتّب", "items_ar": ["A", "B"],
             "correct_sequence": [1, 0]},
        ],
    }
    seed_quiz(conn, doc)
    qs = get_questions(conn, get_quiz_by_slug(conn, "mix")["id"])
    m = _json.loads(qs[0]["data_json"])
    assert m["correct_pairs"] == [[0, 1], [1, 0]] and m["left_ar"] == ["L0", "L1"]
    o = _json.loads(qs[1]["data_json"])
    assert o["correct_sequence"] == [1, 0] and o["items_ar"] == ["A", "B"]
```

(`seed_quiz` and `SAMPLE_DOC` are already imported at the top of `test_seed.py`.)

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_seed.py -k match_and_order -v`
Expected: FAIL — `KeyError: 'options_ar'` (current seed assumes option types).

- [ ] **Step 3: Edit `backend/app/seed.py`** — replace the per-question `data` build inside `seed_quiz`'s loop:

Replace:
```python
    for order, q in enumerate(doc["questions"]):
        data = {"options_ar": q["options_ar"], "correct_index": q["correct_index"]}
```
with:
```python
    for order, q in enumerate(doc["questions"]):
        if q["type"] in ("mcq", "tf", "image"):
            data = {"options_ar": q["options_ar"], "correct_index": q["correct_index"]}
        elif q["type"] == "match":
            data = {"left_ar": q["left_ar"], "right_ar": q["right_ar"], "correct_pairs": q["correct_pairs"]}
        elif q["type"] == "order":
            data = {"items_ar": q["items_ar"], "correct_sequence": q["correct_sequence"]}
        else:
            data = {}
```

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_seed.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/app/seed.py backend/tests/test_seed.py
git commit -m "feat: seed match/order payloads"
```

---

### Task 5: Badges engine — `app/badges.py`

**Files:**
- Create: `backend/app/badges.py`, `backend/tests/test_badges.py`

**Interfaces:**
- Consumes: a `conn` with the Task 1 schema (badges UNIQUE).
- Produces:
  - `app.badges.evaluate(summary: dict) -> list[str]` where `summary` keys are `accuracy: float, max_streak: int, avg_speed_bonus: float, is_first_finish: bool`.
  - `app.badges.award(conn, contestant_id: int, codes: list[str], now: str) -> list[str]` — `INSERT OR IGNORE`; returns codes newly inserted.
  - `app.badges.get_badges(conn, contestant_id: int) -> list[str]`.
  - `app.badges.top_badge(conn, contestant_id: int) -> str | None` — priority `perfect_quiz > streak_master > speed_demon > first_finish`.
- Constant `app.badges.ALL_CODES = ["perfect_quiz", "speed_demon", "streak_master", "first_finish"]`.

- [ ] **Step 1: Write failing tests** `backend/tests/test_badges.py`

```python
from app.badges import evaluate, award, get_badges, top_badge


def test_evaluate_all_conditions():
    s = {"accuracy": 1.0, "max_streak": 6, "avg_speed_bonus": 40.0, "is_first_finish": True}
    codes = set(evaluate(s))
    assert codes == {"perfect_quiz", "streak_master", "speed_demon", "first_finish"}


def test_evaluate_none():
    s = {"accuracy": 0.5, "max_streak": 2, "avg_speed_bonus": 10.0, "is_first_finish": False}
    assert evaluate(s) == []


def test_evaluate_thresholds():
    assert "speed_demon" in evaluate({"accuracy": 0, "max_streak": 0, "avg_speed_bonus": 35.0, "is_first_finish": False})
    assert "speed_demon" not in evaluate({"accuracy": 0, "max_streak": 0, "avg_speed_bonus": 34.9, "is_first_finish": False})
    assert "streak_master" in evaluate({"accuracy": 0, "max_streak": 5, "avg_speed_bonus": 0, "is_first_finish": False})


def test_award_idempotent_and_returns_new(conn):
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.commit()
    new1 = award(conn, 1, ["perfect_quiz", "first_finish"], "2026-06-26T10:00:00")
    assert set(new1) == {"perfect_quiz", "first_finish"}
    new2 = award(conn, 1, ["perfect_quiz", "speed_demon"], "2026-06-26T10:01:00")
    assert new2 == ["speed_demon"]
    assert set(get_badges(conn, 1)) == {"perfect_quiz", "first_finish", "speed_demon"}


def test_top_badge_priority(conn):
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.commit()
    award(conn, 1, ["first_finish", "streak_master"], "2026-06-26T10:00:00")
    assert top_badge(conn, 1) == "streak_master"
    award(conn, 1, ["perfect_quiz"], "2026-06-26T10:01:00")
    assert top_badge(conn, 1) == "perfect_quiz"
    assert top_badge(conn, 999) is None
```

(Uses the existing `conn` fixture from `tests/conftest.py`, which builds the current schema via `init_schema`. Task 1 updated that schema, so badges UNIQUE is present.)

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_badges.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.badges'`.

- [ ] **Step 3: Create `backend/app/badges.py`**

```python
import sqlite3

ALL_CODES = ["perfect_quiz", "speed_demon", "streak_master", "first_finish"]
_PRIORITY = ["perfect_quiz", "streak_master", "speed_demon", "first_finish"]
SPEED_DEMON_MIN_AVG_BONUS = 35.0
STREAK_MASTER_MIN = 5


def evaluate(summary: dict) -> list[str]:
    codes = []
    if summary.get("accuracy", 0) >= 1.0:
        codes.append("perfect_quiz")
    if summary.get("avg_speed_bonus", 0) >= SPEED_DEMON_MIN_AVG_BONUS:
        codes.append("speed_demon")
    if summary.get("max_streak", 0) >= STREAK_MASTER_MIN:
        codes.append("streak_master")
    if summary.get("is_first_finish", False):
        codes.append("first_finish")
    return codes


def award(conn: sqlite3.Connection, contestant_id: int, codes: list[str], now: str) -> list[str]:
    new = []
    for code in codes:
        cur = conn.execute(
            "INSERT OR IGNORE INTO badges (contestant_id, code, earned_at) VALUES (?, ?, ?)",
            (contestant_id, code, now),
        )
        if cur.rowcount:
            new.append(code)
    conn.commit()
    return new


def get_badges(conn, contestant_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT code FROM badges WHERE contestant_id = ?", (contestant_id,)
    ).fetchall()
    return [r["code"] for r in rows]


def top_badge(conn, contestant_id: int):
    earned = set(get_badges(conn, contestant_id))
    for code in _PRIORITY:
        if code in earned:
            return code
    return None
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_badges.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/badges.py backend/tests/test_badges.py
git commit -m "feat: badges engine (evaluate/award/get/top)"
```

---

### Task 6: Auto-DM — `app/notify.py`

**Files:**
- Create: `backend/app/notify.py`, `backend/tests/test_notify.py`

**Interfaces:**
- Consumes: `app.config.settings.bot_token`.
- Produces: `app.notify.send_report_dm(user_id: int, text: str, *, token: str | None = None) -> bool` — POSTs `sendMessage` via `httpx`; returns True on HTTP 200, False on any error or empty token. **Never raises.**

- [ ] **Step 1: Write failing tests** `backend/tests/test_notify.py`

```python
import app.notify as notify


def test_disabled_when_no_token():
    assert notify.send_report_dm(1, "hi", token="") is False


def test_success(monkeypatch):
    calls = {}

    class FakeResp:
        status_code = 200

    def fake_post(url, json, timeout):
        calls["url"] = url
        calls["json"] = json
        return FakeResp()

    monkeypatch.setattr(notify.httpx, "post", fake_post)
    ok = notify.send_report_dm(42, "نتيجتك", token="123:ABC")
    assert ok is True
    assert "sendMessage" in calls["url"] and calls["json"]["chat_id"] == 42


def test_never_raises_on_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(notify.httpx, "post", boom)
    assert notify.send_report_dm(42, "x", token="123:ABC") is False
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_notify.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.notify'`.

- [ ] **Step 3: Create `backend/app/notify.py`**

```python
import httpx

from app.config import settings


def send_report_dm(user_id: int, text: str, *, token: str | None = None) -> bool:
    tok = settings.bot_token if token is None else token
    if not tok:
        return False
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id": user_id, "text": text},
            timeout=3.0,
        )
        return resp.status_code == 200
    except Exception:
        return False
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_notify.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/notify.py backend/tests/test_notify.py
git commit -m "feat: fire-and-forget report auto-DM via Telegram API"
```

---

### Task 7: Models — overall leaderboard + max_streak setter

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_seed.py` is unaffected; add `backend/tests/test_models_ext.py`

**Interfaces:**
- Produces:
  - `app.models.leaderboard_overall(conn, limit=20) -> list[Row]` with columns `first_name, total_score` (sum of each contestant's best score per quiz), descending.
  - `app.models.set_attempt_max_streak(conn, attempt_id: int, max_streak: int) -> None`.

- [ ] **Step 1: Write failing tests** `backend/tests/test_models_ext.py`

```python
from app.models import (
    upsert_contestant, create_attempt, finish_attempt,
    leaderboard_overall, set_attempt_max_streak,
)


def test_set_max_streak(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 1, "first_name": "A"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-26T10:00:00")
    set_attempt_max_streak(conn, aid, 4)
    row = conn.execute("SELECT max_streak FROM attempts WHERE id=?", (aid,)).fetchone()
    assert row["max_streak"] == 4


def test_leaderboard_overall_sums_best_per_quiz(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 1, "first_name": "A"})
    # two attempts on the same quiz: best is 200
    for sc in (120, 200):
        aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-26T10:00:00")
        finish_attempt(conn, aid, sc, 1.0, 1000, "2026-06-26T10:00:05")
    board = leaderboard_overall(conn)
    assert board[0]["first_name"] == "A"
    assert board[0]["total_score"] == 200
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_models_ext.py -v`
Expected: FAIL — `ImportError: cannot import name 'leaderboard_overall'`.

- [ ] **Step 3: Append to `backend/app/models.py`**

```python
def set_attempt_max_streak(conn, attempt_id, max_streak):
    conn.execute("UPDATE attempts SET max_streak=? WHERE id=?", (max_streak, attempt_id))
    conn.commit()


def leaderboard_overall(conn, limit=20):
    return conn.execute(
        """
        SELECT c.first_name AS first_name, SUM(best.best_score) AS total_score
        FROM (
            SELECT contestant_id, quiz_id, MAX(total_score) AS best_score
            FROM attempts WHERE finished_at IS NOT NULL
            GROUP BY contestant_id, quiz_id
        ) best
        JOIN contestants c ON c.telegram_user_id = best.contestant_id
        GROUP BY best.contestant_id
        ORDER BY total_score DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_models_ext.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models_ext.py
git commit -m "feat: overall leaderboard and max_streak setter"
```

---

### Task 8: Report builder — handle match/order + badges + max_streak

**Files:**
- Modify: `backend/app/report.py`
- Modify: `backend/tests/test_report.py` (append)

**Interfaces:**
- Consumes: `app.badges.get_badges`.
- Produces: `build_report` now tolerates match/order answers (no `correct_index`) and includes per-item `type`, `fraction`, and a human-readable `your_ar`/`correct_ar` summary; the report dict gains `max_streak` and `all_badges`. `format_report_text` appends a badges line.

- [ ] **Step 1: Append failing tests** to `backend/tests/test_report.py`

```python
from app.models import record_answer
from app.badges import award


def test_report_includes_max_streak_and_badges(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 3, "first_name": "Z"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    qs = get_questions(conn, quiz_id)
    record_answer(conn, aid, qs[0]["id"], {"index": 2}, True, 1000, 150)
    finish_attempt(conn, aid, 150, 1.0, 1500, "2026-06-25T10:00:05")
    conn.execute("UPDATE attempts SET max_streak=2 WHERE id=?", (aid,))
    conn.commit()
    award(conn, uid, ["perfect_quiz"], "2026-06-25T10:00:05")
    report = build_report(conn, aid)
    assert report["max_streak"] == 2
    assert "perfect_quiz" in report["all_badges"]


def test_report_handles_order_answer(seeded):
    conn, quiz_id = seeded
    # add an order question directly
    import json as _j
    conn.execute(
        "INSERT INTO questions (quiz_id,type,prompt_ar,base_points,explanation_ar,source_page,data_json,display_order) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (quiz_id, "order", "رتّب", 100, "", 1,
         _j.dumps({"items_ar": ["A", "B"], "correct_sequence": [1, 0]}), 5),
    )
    conn.commit()
    qid = conn.execute("SELECT id FROM questions WHERE type='order'").fetchone()["id"]
    uid = upsert_contestant(conn, {"id": 4, "first_name": "Q"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    record_answer(conn, aid, qid, {"sequence": [1, 0]}, True, 1000, 100)
    finish_attempt(conn, aid, 100, 1.0, 1000, "2026-06-25T10:00:05")
    report = build_report(conn, aid)
    item = report["items"][0]
    assert item["type"] == "order"
    assert item["is_correct"] is True
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_report.py -k "max_streak or order_answer" -v`
Expected: FAIL — `KeyError: 'correct_index'` (current build_report assumes option types) / missing `max_streak`.

- [ ] **Step 3: Rewrite `build_report` in `backend/app/report.py`** (keep `format_report_text` below it; only its last line changes). Replace the whole `build_report` function with:

```python
def build_report(conn, attempt_id: int) -> dict:
    attempt = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    answers = conn.execute(
        "SELECT * FROM answers WHERE attempt_id = ? ORDER BY id", (attempt_id,)
    ).fetchall()

    items = []
    for ans in answers:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (ans["question_id"],)).fetchone()
        data = json.loads(q["data_json"])
        given = json.loads(ans["given_json"])
        asset = conn.execute(
            "SELECT file_path FROM assets WHERE question_id = ? LIMIT 1", (q["id"],)
        ).fetchone()

        your_ar, correct_ar = _describe(q["type"], data, given)
        items.append({
            "type": q["type"],
            "prompt_ar": q["prompt_ar"],
            "is_correct": bool(ans["is_correct"]),
            "your_ar": your_ar,
            "correct_ar": correct_ar,
            "explanation_ar": q["explanation_ar"],
            "source_page": q["source_page"],
            "asset_file": asset["file_path"] if asset else None,
        })

    rank_row = conn.execute(
        """SELECT COUNT(*) + 1 AS rank FROM (
               SELECT a.contestant_id, MAX(a.total_score) AS best
               FROM attempts a WHERE a.quiz_id = ? AND a.finished_at IS NOT NULL
               GROUP BY a.contestant_id
           ) WHERE best > ?""",
        (attempt["quiz_id"], attempt["total_score"]),
    ).fetchone()

    from app.badges import get_badges
    return {
        "total_score": attempt["total_score"],
        "accuracy": attempt["accuracy"],
        "duration_ms": attempt["duration_ms"],
        "max_streak": attempt["max_streak"],
        "rank": rank_row["rank"],
        "items": items,
        "all_badges": get_badges(conn, attempt["contestant_id"]),
    }


def _describe(qtype, data, given):
    """Return (your_ar, correct_ar) human-readable answer strings."""
    if qtype in ("mcq", "tf", "image"):
        opts = data["options_ar"]
        gi = given.get("index")
        your = opts[gi] if isinstance(gi, int) and 0 <= gi < len(opts) else "—"
        return your, opts[data["correct_index"]]
    if qtype == "match":
        left, right = data["left_ar"], data["right_ar"]
        correct = "، ".join(f"{left[li]}↔{right[ri]}" for li, ri in data["correct_pairs"])
        gp = given.get("pairs", [])
        your = "، ".join(f"{left[li]}↔{right[ri]}" for li, ri in gp if li < len(left) and ri < len(right)) or "—"
        return your, correct
    if qtype == "order":
        items = data["items_ar"]
        correct = " ← ".join(items[i] for i in data["correct_sequence"])
        gs = given.get("sequence", [])
        your = " ← ".join(items[i] for i in gs if 0 <= i < len(items)) or "—"
        return your, correct
    return "—", "—"
```

- [ ] **Step 4: Update `format_report_text`** — append a badges-aware line. Replace its `return` with:

```python
    correct = sum(1 for it in report["items"] if it["is_correct"])
    total = len(report["items"])
    pct = round(report["accuracy"] * 100)
    lines = [
        f"🏁 نتيجتك في: {title_ar}",
        f"النقاط: {report['total_score']}",
        f"الإجابات الصحيحة: {correct}/{total} ({pct}%)",
        f"الترتيب: #{report['rank']}",
    ]
    if report.get("all_badges"):
        lines.append("الأوسمة: " + " ".join(_BADGE_AR.get(b, b) for b in report["all_badges"]))
    return "\n".join(lines)
```

And add this mapping at the top of `report.py` (after `import json`):

```python
_BADGE_AR = {
    "perfect_quiz": "🏅الإتقان",
    "speed_demon": "⚡البرق",
    "streak_master": "🔥السلسلة",
    "first_finish": "🌟البداية",
}
```

Note: the Phase 1 `test_report.py` tests reference `report["items"][0]["correct_index"]` and `given_index`. Those keys are replaced by `your_ar`/`correct_ar`. **Update the two Phase 1 assertions** in `test_report.py` accordingly:
- `assert first["correct_index"] == 2` → `assert first["correct_ar"] == report_options_correct` is awkward; instead change them to `assert first["is_correct"] is True` and `assert "اليسار" in report["items"][1]["correct_ar"] or report["items"][1]["asset_file"]`. Concretely, replace the body of `test_build_report_shape` assertions about `correct_index`/`given_index` with:

```python
    assert first["is_correct"] is True
    assert first["type"] == "mcq"
```

- [ ] **Step 5: Run them, expect pass**

Run: `cd backend && pytest tests/test_report.py -v`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add backend/app/report.py backend/tests/test_report.py
git commit -m "feat: report handles match/order, badges, max_streak"
```

---

### Task 9: API — submit refactor, badges, auto-DM, overall board, /me/badges

**Files:**
- Modify: `backend/app/api.py`
- Modify: `backend/tests/test_api.py` (append)

**Interfaces:**
- Consumes: `scoring.grade`, `scoring.score_fraction`, `badges.evaluate/award`, `notify.send_report_dm`, `models.set_attempt_max_streak`, `models.leaderboard_overall`, `badges.top_badge`, `badges.get_badges`.
- Produces:
  - `POST /quizzes/{slug}/submit` — grades all types via `grade`, persists `max_streak`, awards badges, fires the DM, returns report with `earned_now` + `all_badges`.
  - `GET /quizzes/{slug}/questions` — exposes type-specific non-answer fields.
  - `GET /leaderboard?scope=overall|quiz&slug=` — adds overall; rows include `top_badge`.
  - `GET /me/badges` — initData-authenticated; returns `{"badges": [...]}`.

- [ ] **Step 1: Append failing tests** to `backend/tests/test_api.py`

```python
def _seed_order_question(client_db_conn):
    import json as _j
    client_db_conn.execute(
        "INSERT INTO questions (quiz_id,type,prompt_ar,base_points,explanation_ar,source_page,data_json,display_order) "
        "VALUES ((SELECT id FROM quizzes WHERE slug='journals'),'order','رتّب',100,'',1,?,9)",
        (_j.dumps({"items_ar": ["A", "B", "C"], "correct_sequence": [2, 0, 1]}),),
    )
    client_db_conn.commit()


def test_questions_exposes_order_items_no_answer(api_client):
    main_module = __import__("app.main", fromlist=["app"])
    _seed_order_question(main_module._conn)
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    oq = [q for q in qs if q["type"] == "order"][0]
    assert oq["items_ar"] == ["A", "B", "C"]
    assert "correct_sequence" not in oq


def test_submit_order_partial_and_first_finish_badge(api_client, monkeypatch):
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    main_module = __import__("app.main", fromlist=["app"])
    _seed_order_question(main_module._conn)
    init = _init_data({"id": 555, "first_name": "Lina"})
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    oq = [q for q in qs if q["type"] == "order"][0]
    # correct order -> full credit
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": [{"question_id": oq["id"], "sequence": [2, 0, 1], "time_ms": 800}], "duration_ms": 800},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["items"][0]["is_correct"] is True
    assert "first_finish" in body["earned_now"]


def test_me_badges_requires_initdata(api_client):
    assert api_client.get("/api/me/badges", headers={"X-Init-Data": "bad&hash=x"}).status_code == 401


def test_overall_leaderboard(api_client, monkeypatch):
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    init = _init_data({"id": 7, "first_name": "Omar"})
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    mcq = [q for q in qs if q["type"] in ("mcq", "tf", "image")][0]
    api_client.post("/api/quizzes/journals/submit", headers={"X-Init-Data": init},
                    json={"answers": [{"question_id": mcq["id"], "index": 0, "time_ms": 500}], "duration_ms": 500})
    board = api_client.get("/api/leaderboard?scope=overall").json()
    assert board and "total_score" in board[0] and "top_badge" in board[0]
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_api.py -k "order or me_badges or overall" -v`
Expected: FAIL (routes/fields not present).

- [ ] **Step 3: Rewrite `get_questions` in `backend/app/api.py`** to expose per-type fields:

```python
@router.get("/quizzes/{slug}/questions")
def get_questions(slug: str, request: Request):
    conn = _conn(request)
    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")
    out = []
    for q in models.get_questions(conn, quiz["id"]):
        data = json.loads(q["data_json"])
        asset = models.get_asset_for_question(conn, q["id"])
        item = {
            "id": q["id"],
            "type": q["type"],
            "prompt_ar": q["prompt_ar"],
            "base_points": q["base_points"],
            "asset_file": asset["file_path"] if asset else None,
        }
        if q["type"] in ("mcq", "tf", "image"):
            item["options_ar"] = data["options_ar"]
        elif q["type"] == "match":
            item["left_ar"] = data["left_ar"]
            item["right_ar"] = data["right_ar"]
        elif q["type"] == "order":
            item["items_ar"] = data["items_ar"]
        out.append(item)
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]}, "questions": out}
```

- [ ] **Step 4: Rewrite `submit` in `backend/app/api.py`** to use `grade`/`score_fraction`, badges, DM:

```python
@router.post("/quizzes/{slug}/submit")
def submit(slug: str, payload: dict, request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")

    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")

    qrows = {q["id"]: q for q in models.get_questions(conn, quiz["id"])}

    contestant_id = models.upsert_contestant(conn, user)
    is_first_finish = conn.execute(
        "SELECT COUNT(*) AS n FROM attempts WHERE contestant_id=? AND finished_at IS NOT NULL",
        (contestant_id,),
    ).fetchone()["n"] == 0
    attempt_id = models.create_attempt(conn, contestant_id, quiz["id"], "async", _now(conn))

    total = 0
    correct_count = 0
    streak = 0
    max_streak = 0
    bonus_sum = 0
    answers = payload.get("answers", [])
    for a in answers:
        qid = a.get("question_id")
        q = qrows.get(qid)
        if not q:
            continue
        data = json.loads(q["data_json"])
        fraction, is_full = grade(q["type"], data, a)
        time_ms = int(a.get("time_ms", 60000))
        pts = score_fraction(q["base_points"], fraction, time_ms, streak)
        from app.scoring import speed_bonus
        bonus_sum += speed_bonus(time_ms)
        streak = streak + 1 if is_full else 0
        max_streak = max(max_streak, streak)
        if is_full:
            correct_count += 1
        total += pts
        models.record_answer(conn, attempt_id, qid, a, is_full, int(a.get("time_ms", 0)), pts)

    n = len(answers)
    accuracy = correct_count / n if n else 0.0
    models.finish_attempt(conn, attempt_id, total, accuracy, int(payload.get("duration_ms", 0)), _now(conn))
    models.set_attempt_max_streak(conn, attempt_id, max_streak)

    summary = {
        "accuracy": accuracy,
        "max_streak": max_streak,
        "avg_speed_bonus": (bonus_sum / n) if n else 0.0,
        "is_first_finish": is_first_finish,
    }
    earned_now = badges.award(conn, contestant_id, badges.evaluate(summary), _now(conn))

    from app.report import build_report, format_report_text
    report = build_report(conn, attempt_id)
    report["attempt_id"] = attempt_id
    report["earned_now"] = earned_now

    notify.send_report_dm(contestant_id, format_report_text(report, quiz["title_ar"]))
    return report
```

- [ ] **Step 5: Rewrite `get_leaderboard` and add `me_badges`** in `backend/app/api.py`:

```python
@router.get("/leaderboard")
def get_leaderboard(request: Request, scope: str = "quiz", slug: str = ""):
    conn = _conn(request)
    if scope == "overall":
        rows = models.leaderboard_overall(conn)
        return [
            {"first_name": r["first_name"], "total_score": r["total_score"],
             "top_badge": _top_badge_for_name(conn, r["first_name"])}
            for r in rows
        ]
    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")
    rows = models.leaderboard(conn, quiz["id"])
    return [
        {"first_name": r["first_name"], "best_score": r["best_score"],
         "top_badge": _top_badge_for_name(conn, r["first_name"])}
        for r in rows
    ]


def _top_badge_for_name(conn, first_name):
    row = conn.execute(
        "SELECT telegram_user_id FROM contestants WHERE first_name=? LIMIT 1", (first_name,)
    ).fetchone()
    return badges.top_badge(conn, row["telegram_user_id"]) if row else None


@router.get("/me/badges")
def me_badges(request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    return {"badges": badges.get_badges(conn, int(user["id"]))}
```

- [ ] **Step 6: Update the imports at the top of `backend/app/api.py`** — replace the scoring import and add new ones:

```python
from app import models, badges, notify
from app.auth import validate_init_data, AuthError
from app.config import settings
from app.scoring import grade, score_fraction
```

- [ ] **Step 7: Run the API tests, expect pass**

Run: `cd backend && pytest tests/test_api.py -v`
Expected: PASS (Phase 1 API tests + the new ones). Note the Phase 1 `test_submit_scores_and_returns_report` still passes because option-type grading is unchanged.

- [ ] **Step 8: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass, output pristine.

- [ ] **Step 9: Commit**

```bash
git add backend/app/api.py backend/tests/test_api.py
git commit -m "feat: submit grades all types + badges + auto-DM; overall board; /me/badges"
```

---

### Task 10: Frontend — match/order drag renderers (pointer events)

**Files:**
- Modify: `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`

**Interfaces:**
- Consumes: `GET /questions` (type-specific fields), `POST /submit` (match `{pairs}`, order `{sequence}`).
- Produces: the runner renders `match` and `order` and builds the correct answer object; existing mcq/tf/image unchanged.

- [ ] **Step 1: Add styles** to `frontend/styles.css` (append):

```css
.match-wrap { display:flex; gap:10px; }
.match-col { flex:1; display:flex; flex-direction:column; gap:8px; }
.slot { min-height:52px; border:2px dashed #394a5a; border-radius:12px;
  display:flex; align-items:center; justify-content:center; background:#141a28; padding:6px; }
.chip { background:var(--accent); color:#fff; border-radius:10px; padding:12px; text-align:center;
  touch-action:none; user-select:none; }
.chip.dragging { opacity:.6; }
.order-list { display:flex; flex-direction:column; gap:8px; }
.order-row { background:var(--card); border-radius:12px; padding:14px; display:flex; align-items:center;
  gap:10px; touch-action:none; user-select:none; }
.order-row .handle { opacity:.6; }
.order-row.dragging { opacity:.6; }
.runner-submit { background:var(--good); font-weight:600; }
```

(If `#3a4straight` looks odd, it's a typo guard — use `#394` as shown on the next line; keep only the valid `border:2px dashed #394;`.)

- [ ] **Step 2: Add a pointer-drag helper and renderers** to `frontend/app.js`. Insert before `function renderQuestion()`:

```javascript
// --- generic pointer drag: returns the element under the pointer matching selector ---
function elementUnder(x, y, selector) {
  const el = document.elementFromPoint(x, y);
  return el ? el.closest(selector) : null;
}

function renderMatch(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "match-wrap";
  const leftCol = document.createElement("div");
  leftCol.className = "match-col";
  const rightCol = document.createElement("div");
  rightCol.className = "match-col";
  wrap.append(leftCol, rightCol);
  opts.appendChild(wrap);

  // left fixed rows, each with a drop slot
  q.left_ar.forEach((text, li) => {
    const row = document.createElement("div");
    row.innerHTML = `<div style="margin-bottom:4px">${text}</div>`;
    const slot = document.createElement("div");
    slot.className = "slot";
    slot.dataset.left = li;
    row.appendChild(slot);
    leftCol.appendChild(row);
  });

  // right draggable chips, shuffled, carrying original index
  const order = q.right_ar.map((_, i) => i).sort(() => Math.random() - 0.5);
  order.forEach((ri) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = q.right_ar[ri];
    chip.dataset.right = ri;
    rightCol.appendChild(chip);
    makeChipDraggable(chip, rightCol);
  });

  ensureSubmitButton(() => {
    const pairs = [];
    document.querySelectorAll(".slot").forEach((slot) => {
      const chip = slot.querySelector(".chip");
      if (chip) pairs.push([Number(slot.dataset.left), Number(chip.dataset.right)]);
    });
    answerComplex({ pairs });
  });
}

function makeChipDraggable(chip, home) {
  chip.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    chip.setPointerCapture(e.pointerId);
    chip.classList.add("dragging");
    const move = (ev) => {
      chip.style.position = "fixed";
      chip.style.left = ev.clientX - 30 + "px";
      chip.style.top = ev.clientY - 20 + "px";
      chip.style.zIndex = 1000;
    };
    const up = (ev) => {
      chip.releasePointerCapture(e.pointerId);
      chip.classList.remove("dragging");
      chip.style.position = "";
      chip.style.left = chip.style.top = chip.style.zIndex = "";
      const slot = elementUnder(ev.clientX, ev.clientY, ".slot");
      if (slot) {
        const existing = slot.querySelector(".chip");
        if (existing) home.appendChild(existing);
        slot.appendChild(chip);
      } else {
        home.appendChild(chip);
      }
      chip.removeEventListener("pointermove", move);
      chip.removeEventListener("pointerup", up);
    };
    chip.addEventListener("pointermove", move);
    chip.addEventListener("pointerup", up);
  });
}

function renderOrder(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  const list = document.createElement("div");
  list.className = "order-list";
  opts.appendChild(list);
  const order = q.items_ar.map((_, i) => i).sort(() => Math.random() - 0.5);
  order.forEach((oi) => {
    const row = document.createElement("div");
    row.className = "order-row";
    row.dataset.orig = oi;
    row.innerHTML = `<span class="handle">≡</span><span>${q.items_ar[oi]}</span>`;
    list.appendChild(row);
    makeRowReorderable(row, list);
  });
  ensureSubmitButton(() => {
    const sequence = [...list.querySelectorAll(".order-row")].map((r) => Number(r.dataset.orig));
    answerComplex({ sequence });
  });
}

function makeRowReorderable(row, list) {
  row.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    row.setPointerCapture(e.pointerId);
    row.classList.add("dragging");
    const move = (ev) => {
      const over = elementUnder(ev.clientX, ev.clientY, ".order-row");
      if (over && over !== row) {
        const rect = over.getBoundingClientRect();
        const before = ev.clientY < rect.top + rect.height / 2;
        list.insertBefore(row, before ? over : over.nextSibling);
      }
    };
    const up = () => {
      row.releasePointerCapture(e.pointerId);
      row.classList.remove("dragging");
      row.removeEventListener("pointermove", move);
      row.removeEventListener("pointerup", up);
    };
    row.addEventListener("pointermove", move);
    row.addEventListener("pointerup", up);
  });
}

function ensureSubmitButton(onSubmit) {
  const opts = document.getElementById("q-options");
  const btn = document.createElement("button");
  btn.className = "runner-submit";
  btn.textContent = "تأكيد";
  btn.onclick = () => { clearInterval(state.timer); onSubmit(); };
  opts.appendChild(btn);
}

function answerComplex(givenExtra) {
  const q = state.questions[state.idx];
  state.answers.push({ question_id: q.id, time_ms: Date.now() - state.qStart, ...givenExtra });
  state.idx += 1;
  if (state.idx < state.questions.length) renderQuestion();
  else submit();
}
```

- [ ] **Step 3: Branch `renderQuestion()`** in `frontend/app.js` to dispatch by type. Replace the option-building block (the part after setting prompt/image, starting at `const opts = document.getElementById("q-options");`) with:

```javascript
  const q2type = q.type;
  if (q2type === "match") { renderMatch(q); }
  else if (q2type === "order") { renderOrder(q); }
  else {
    const opts = document.getElementById("q-options");
    opts.innerHTML = "";
    q.options_ar.forEach((text, i) => {
      const btn = document.createElement("button");
      btn.className = "opt";
      btn.textContent = text;
      btn.onclick = () => answer(i);
      opts.appendChild(btn);
    });
  }

  state.qStart = Date.now();
  const timerEl = document.getElementById("timer");
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    timerEl.textContent = ((Date.now() - state.qStart) / 1000).toFixed(1) + "s";
  }, 100);
```

(Ensure the old timer-start block that followed the options loop is removed so it isn't duplicated.)

- [ ] **Step 4: Manual smoke test**

Run: `cd backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --reload --port 8000`
Open `http://localhost:8000/app/`. Add a temporary order/match question via seed if needed (Task 12 adds real ones). Verify: an order question shows draggable rows that reorder; a match question lets you drag right chips into left slots; the **تأكيد** button advances. (Submit 401 in a plain browser is expected.)

- [ ] **Step 5: Commit**

```bash
git add frontend/app.js frontend/index.html frontend/styles.css
git commit -m "feat: Mini App match/order drag renderers (pointer events)"
```

---

### Task 11: Frontend — badges (report pop, my-badges screen, leaderboard icons, overall toggle)

**Files:**
- Modify: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`

**Interfaces:**
- Consumes: report `earned_now`/`all_badges`, `GET /me/badges`, leaderboard rows' `top_badge`, `scope=overall`.

- [ ] **Step 1: Add markup** to `frontend/index.html` — a badges screen and a home button. After the `screen-board` section add:

```html
    <section id="screen-badges" class="screen hidden">
      <h2>أوسمتي</h2>
      <div id="badges-grid"></div>
      <button id="btn-badges-home">العودة</button>
    </section>
```

In `screen-home`, after `<div id="quiz-list"></div>` add:
```html
      <button id="btn-my-badges" class="quiz-card">🏅 أوسمتي</button>
```

In `screen-report`, before `#btn-board`, add a badges row:
```html
      <div id="report-badges"></div>
```

In `screen-board`, after `<h2>لوحة الصدارة</h2>` add a scope toggle:
```html
      <div class="board-toggle">
        <button id="board-quiz" class="quiz-card">هذه المسابقة</button>
        <button id="board-overall" class="quiz-card">الإجمالي</button>
      </div>
```

- [ ] **Step 2: Add styles** to `frontend/styles.css` (append):

```css
.badges-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
.badge { background:var(--card); border-radius:12px; padding:14px; text-align:center; }
.badge.locked { opacity:.35; filter:grayscale(1); }
.badge .ico { font-size:1.8rem; }
.report-badge { display:inline-block; background:var(--accent); color:#fff; border-radius:10px;
  padding:6px 10px; margin:4px 2px; }
.board-toggle { display:flex; gap:8px; margin-bottom:8px; }
.lb-badge { margin-inline-start:6px; }
```

- [ ] **Step 3: Add badge metadata + screen logic** to `frontend/app.js`. Insert near the top (after the `screens` array):

```javascript
const BADGES = {
  perfect_quiz: { ico: "🏅", name_ar: "الإتقان" },
  speed_demon: { ico: "⚡", name_ar: "البرق" },
  streak_master: { ico: "🔥", name_ar: "السلسلة" },
  first_finish: { ico: "🌟", name_ar: "البداية" },
};
const BADGE_ORDER = ["perfect_quiz", "speed_demon", "streak_master", "first_finish"];
```

Add `"badges"` to the `screens` array: `const screens = ["home", "runner", "report", "board", "badges"];`

Add these functions:

```javascript
async function loadBadges() {
  let earned = [];
  try { earned = (await api("/me/badges", { headers: { "X-Init-Data": tg.initData } })).badges; }
  catch (e) { earned = []; }
  const grid = document.getElementById("badges-grid");
  grid.className = "badges-grid";
  grid.innerHTML = "";
  BADGE_ORDER.forEach((code) => {
    const b = BADGES[code];
    const div = document.createElement("div");
    div.className = "badge" + (earned.includes(code) ? "" : " locked");
    div.innerHTML = `<div class="ico">${b.ico}</div><div>${b.name_ar}</div>`;
    grid.appendChild(div);
  });
  document.getElementById("btn-badges-home").onclick = loadHome;
  show("badges");
}
```

- [ ] **Step 4: Update `renderReport` for the new report-item keys AND show earned badges.** Task 8 changed report items from `options_ar`/`given_index`/`correct_index` to `type`/`your_ar`/`correct_ar`/`is_correct`. Replace the whole `renderReport(report)` function in `frontend/app.js` with:

```javascript
function renderReport(report) {
  const correct = report.items.filter((i) => i.is_correct).length;
  document.getElementById("report-summary").innerHTML =
    `<div class="summary-big">${report.total_score} نقطة</div>` +
    `<div style="text-align:center">صحيح ${correct}/${report.items.length} — الترتيب #${report.rank}</div>`;

  const badgesBox = document.getElementById("report-badges");
  badgesBox.innerHTML = "";
  (report.earned_now || []).forEach((code) => {
    const b = BADGES[code];
    const span = document.createElement("span");
    span.className = "report-badge";
    span.textContent = `${b.ico} ${b.name_ar}`;
    badgesBox.appendChild(span);
  });

  const box = document.getElementById("report-items");
  box.innerHTML = "";
  report.items.forEach((it) => {
    const div = document.createElement("div");
    div.className = "report-item " + (it.is_correct ? "good" : "bad");
    div.innerHTML =
      `<div>${it.prompt_ar}</div>` +
      `<div>إجابتك: ${it.your_ar} ${it.is_correct ? "✅" : "❌"}</div>` +
      (it.is_correct ? "" : `<div>الصحيح: ${it.correct_ar}</div>`) +
      (it.explanation_ar ? `<div>📖 ${it.explanation_ar}` + (it.source_page ? ` (ص ${it.source_page})` : "") + `</div>` : "") +
      (it.asset_file ? `<img src="/content/${it.asset_file}" alt="" />` : "");
    box.appendChild(div);
  });

  document.getElementById("btn-board").onclick = () => loadBoard("quiz");
}
```

- [ ] **Step 5: Wire home + leaderboard scope.** In `loadHome()`, after building the quiz list, add:
```javascript
  document.getElementById("btn-my-badges").onclick = loadBadges;
```

Replace `loadBoard()` with a scope-aware version:
```javascript
async function loadBoard(scope = "quiz") {
  const path = scope === "overall" ? "/leaderboard?scope=overall" : `/leaderboard?scope=quiz&slug=${state.slug}`;
  const board = await api(path);
  const ol = document.getElementById("board-list");
  ol.innerHTML = "";
  board.forEach((r) => {
    const li = document.createElement("li");
    const score = scope === "overall" ? r.total_score : r.best_score;
    const badge = r.top_badge ? `<span class="lb-badge">${BADGES[r.top_badge].ico}</span>` : "";
    li.innerHTML = `${r.first_name} — ${score}${badge}`;
    ol.appendChild(li);
  });
  document.getElementById("board-quiz").onclick = () => loadBoard("quiz");
  document.getElementById("board-overall").onclick = () => loadBoard("overall");
  document.getElementById("btn-home").onclick = loadHome;
  show("board");
}
```

- [ ] **Step 6: Manual smoke test**

Restart uvicorn, open `/app/`. Verify the home has a "🏅 أوسمتي" button opening a locked/unlocked grid; the leaderboard shows a quiz/overall toggle. (Earned badges require an in-Telegram submit; verified end-to-end in Task 13.)

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat: badges UI (report pop, my-badges screen, leaderboard icons, overall toggle)"
```

---

### Task 12: Content — add real match/order questions

**Files:**
- Modify: `content/questions/journals.json`
- Create: assets under `content/assets/journals/` as needed

**Interfaces:**
- Produces: ≥1 `order` and ≥1 `match` question grounded in the journals PDF with real artifacts, schema-valid.

- [ ] **Step 1: Re-read the source** `content/raw/journals.txt` (regenerate if missing: `python scripts/extract.py "المحور الثاني -تصنيف المجلات العلمية.pdf" content/raw/journals.txt`). Identify one ordering concept (e.g. priorities when choosing a publication venue) and one matching concept (e.g. red-flag phrases → predatory tactic names).

- [ ] **Step 2: Source real artifacts (if the question needs one).** Verify network: `python -c "import urllib.request; urllib.request.urlopen('https://doaj.org', timeout=10); print('ok')"`. If OK, download a genuine journal-filter screenshot into `content/assets/journals/` and record its `source_url`; anonymize personal data. If blocked, ask the user to supply it. Do not fabricate.

- [ ] **Step 3: Append the two questions** to `content/questions/journals.json` `questions` array. Example shapes (replace text/indices/asset with real curated content):

```json
{
  "type": "order",
  "prompt_ar": "رتّب هذه المعايير حسب أولويتها عند اختيار مجلة للنشر (الأهم أولاً).",
  "base_points": 120,
  "explanation_ar": "الفهرسة وتصنيف الربع يسبقان سرعة القبول ورسوم النشر.",
  "source_page": 6,
  "items_ar": ["الفهرسة في قواعد معتبرة", "تصنيف الربع (Quartile)", "سرعة القبول", "رسوم النشر (APC)"],
  "correct_sequence": [0, 1, 2, 3]
},
{
  "type": "match",
  "prompt_ar": "طابِق كل عبارة من بريد مجلة محترِسة مع التكتيك الذي تمثّله.",
  "base_points": 120,
  "explanation_ar": "وعود القبول السريع والرسوم الفورية والإطراء المبالغ من علامات المجلات المحترِسة.",
  "source_page": 9,
  "left_ar": ["قبول خلال 48 ساعة", "رسوم تُدفع فورًا قبل المراجعة", "لقد اخترناك لخبرتك الفريدة"],
  "right_ar": ["مراجعة شكلية/غياب التحكيم", "ابتزاز مالي", "إطراء مُصطنع"],
  "correct_pairs": [[0, 0], [1, 1], [2, 2]]
}
```

- [ ] **Step 4: Validate** the file:

Run:
```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/journals.json',encoding='utf-8'))); print('valid')"
```
Expected: `valid`.

- [ ] **Step 5: Commit**

```bash
git add content/questions/journals.json content/assets/journals/
git commit -m "feat: real match/order questions for journals quiz"
```

---

### Task 13: Live migration + re-seed + end-to-end verification

**Files:** none (operational), uses the running compose stack.

- [ ] **Step 1: Rebuild images with the new code**

Run: `docker compose build web bot`
Expected: builds succeed.

- [ ] **Step 2: Migrate the live volume**

Run: `docker compose run --rm web python -m app.migrate`
Expected: prints `migrated: ['attempts.max_streak', 'questions.drop_check', 'badges.unique']` (or `already current` on reruns).

- [ ] **Step 3: Re-seed (idempotent) to load the new questions**

Run:
```bash
docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect; from app.seed import seed_from_file; c=connect('/data/quiz.db'); print('seeded', seed_from_file(c,'/srv/content/questions/journals.json'))"
```
Expected: `seeded 1`.

- [ ] **Step 4: Restart and verify API**

Run:
```bash
docker compose up -d web bot cloudflared
curl -s https://src.mulhamfetna.com/api/quizzes
curl -s "https://src.mulhamfetna.com/api/quizzes/journals/questions" | python -c "import sys,json; qs=json.load(sys.stdin)['questions']; print('types:', sorted({q['type'] for q in qs}))"
curl -s "https://src.mulhamfetna.com/api/leaderboard?scope=overall"
```
Expected: types include `match` and `order`; overall board returns JSON.

- [ ] **Step 5: End-to-end in Telegram (manual)**

- [ ] `/start` → play the journals quiz; reach the order question — rows drag/reorder; reach the match question — chips drag into slots; **تأكيد** advances.
- [ ] Finish → report shows score, and any newly-earned badge chips appear.
- [ ] Received the report as a **bot DM** automatically.
- [ ] Home → **🏅 أوسمتي** shows the badge grid with earned ones unlocked.
- [ ] Leaderboard → quiz/overall toggle works; a badge icon shows next to your name.

- [ ] **Step 6: Commit** any ops notes if `docs/DEPLOY.md` needed a migrate step:

Add to `docs/DEPLOY.md` under a new "Upgrades" note: "After pulling new code: `docker compose run --rm web python -m app.migrate` then re-seed (Step 5), then `docker compose up -d --build`." Then:
```bash
git add docs/DEPLOY.md
git commit -m "docs: upgrade/migration step for deploys"
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- match/order types → Tasks 3 (schema), 4 (seed), 2 (grade), 10 (frontend), 12 (content). ✓
- Partial-credit scoring → Task 2 + Task 9 wiring. ✓
- Badges (4) awarded/persisted → Tasks 1 (UNIQUE), 5 (engine), 9 (award in submit). ✓
- Badge display in 4 places → report pop + my-badges screen + leaderboard icons (Task 11), bot DM (Task 8 `format_report_text`). ✓
- Overall leaderboard → Task 7 (query) + Task 9 (route) + Task 11 (toggle). ✓
- Auto-DM from backend, fire-and-forget → Task 6 + Task 9. ✓
- Migration (drop CHECK, max_streak, badges UNIQUE) → Task 1; live run → Task 13. ✓
- `data_json` payloads / answer shapes → defined once up top; used consistently in Tasks 2/4/8/9/10. ✓

**Placeholder scan:** No "TBD/handle errors" in code steps. The one interactive step is Task 12 Steps 1–3 (reading the PDF, sourcing a real artifact, authoring Arabic content), inherent to the "real source" requirement and bounded by the schema validator (Task 3) + concrete JSON shapes.

**Type consistency:** `grade(qtype, data, given)` and `score_fraction(base, fraction, time_ms, streak_before)` are used identically in Tasks 2 and 9. Answer keys (`index`/`pairs`/`sequence`), stored `data_json` keys (`options_ar`/`correct_index`, `left_ar`/`right_ar`/`correct_pairs`, `items_ar`/`correct_sequence`), and report item keys (`type`, `is_correct`, `your_ar`, `correct_ar`) match across backend (8/9), frontend (10/11), and tests. Badge codes `perfect_quiz`/`speed_demon`/`streak_master`/`first_finish` are identical in `badges.py`, `report.py` `_BADGE_AR`, and frontend `BADGES`.

**Note for the executor:** Task 8 changes report item keys (`correct_index`/`given_index` → `your_ar`/`correct_ar`), so the Phase 1 `test_report.py` assertions are updated in that task, and the Phase 1 frontend report rendering (which read `it.options_ar[it.given_index]`) is replaced by `it.your_ar`/`it.correct_ar` — update `renderReport` in `app.js` during Task 11 Step 4 (use `it.your_ar`/`it.correct_ar`/`it.is_correct` instead of the old option-index lookups).
```
