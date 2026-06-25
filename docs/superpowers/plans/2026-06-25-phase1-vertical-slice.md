# Phase 1 — Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one quiz (the "classifying scientific journals" session) fully playable end-to-end inside a Telegram Mini App — server-scored, with a detailed per-contestant report and a leaderboard.

**Architecture:** A Python FastAPI backend serves a vanilla HTML/JS Mini App (Arabic, RTL) over HTTPS, exposes a small JSON REST API, validates the contestant's identity from Telegram `initData`, computes scores authoritatively, and persists everything in a local SQLite file via the stdlib `sqlite3` module. A python-telegram-bot process provides the `/start` entry point (a button that opens the Mini App) and DMs each contestant their report. Questions and real-world artifact screenshots are loaded from a curated JSON file by a seed script.

**Tech Stack:** Python 3.14, FastAPI 0.136, Uvicorn, python-telegram-bot 22.8, stdlib `sqlite3`, pytest + httpx (FastAPI `TestClient`). Frontend is dependency-free HTML/CSS/JS plus Telegram's `telegram-web-app.js`.

## Global Constraints

- **Language:** all learner-facing text is **Arabic, RTL**. The Mini App root sets `dir="rtl"` and `lang="ar"`.
- **One quiz in scope:** slug `journals`, from `المحور الثاني -تصنيف المجلات العلمية.pdf`. Other PDFs are out of scope for Phase 1.
- **Question types in scope:** `mcq`, `tf`, `image` only. `match` and `order` are deferred to Phase 2 — do not build them.
- **Scoring is server-authoritative:** the client submits answers + per-question `time_ms`; it never sends a score. `time_ms` is clamped to `[0, 60000]` before use.
- **Identity:** every API call that records data is authenticated by validating Telegram `initData` HMAC with the bot token. No other auth.
- **Storage:** stdlib `sqlite3` only. No ORM. DB file path comes from env `QUIZ_DB_PATH` (default `./quiz.db`).
- **No secrets in git:** `BOT_TOKEN` and other secrets live in `.env` (already gitignored). Tests must never require a real bot token.
- **Python package root:** all backend code lives under `backend/app/` and is imported as `app.<module>`; tests run from `backend/` with `pytest`.
- **Commit after every task** (each task ends with a commit step).

---

## File Structure

```
backend/
  pyproject.toml          # deps + pytest config
  app/
    __init__.py
    config.py             # env-driven settings (BOT_TOKEN, DB path, public URL)
    db.py                 # sqlite3 connection + schema DDL + low-level helpers
    models.py             # dataclasses for rows + repository functions
    content_schema.py     # validate a question-bank dict; raise on bad data
    scoring.py            # pure scoring functions
    auth.py               # Telegram initData parsing + HMAC validation
    report.py             # build report dict from an attempt; format report text for bot
    api.py                # FastAPI router: quizzes, questions, submit, leaderboard
    main.py               # FastAPI app: mounts api + static Mini App + /health
    seed.py               # load content/questions/<slug>.json into the DB
    bot.py                # python-telegram-bot: /start, /leaderboard, report DM
  tests/
    conftest.py           # fixtures: temp DB, seeded quiz, fake initData
    test_db.py
    test_content_schema.py
    test_scoring.py
    test_auth.py
    test_report.py
    test_api.py
    test_seed.py
scripts/
  extract.py              # pdftotext wrapper -> content/raw/<slug>.txt
frontend/
  index.html              # Mini App shell (RTL)
  styles.css
  app.js                  # screens: home, runner, report, leaderboard
content/
  raw/                    # extract.py output (gitignored)
  questions/journals.json # curated question bank (committed)
  assets/journals/        # real-world screenshots (committed)
Dockerfile
docker-compose.yml
docs/DEPLOY.md
```

---

### Task 1: Project scaffold + health endpoint

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/tests/__init__.py`, `backend/tests/test_api.py`

**Interfaces:**
- Produces: `app.config.settings` (object with `.bot_token: str`, `.db_path: str`, `.public_url: str`); `app.main.app` (FastAPI instance) exposing `GET /health` → `{"status": "ok"}`.

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "gamified-quiz"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.136",
    "uvicorn[standard]>=0.30",
    "python-telegram-bot>=22.8",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `backend/app/__init__.py` and `backend/tests/__init__.py`** (both empty files)

- [ ] **Step 3: Create `backend/app/config.py`**

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: str
    public_url: str


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ.get("BOT_TOKEN", ""),
        db_path=os.environ.get("QUIZ_DB_PATH", "./quiz.db"),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
    )


settings = load_settings()
```

- [ ] **Step 4: Write the failing test** in `backend/tests/test_api.py`

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 5: Run it, expect failure**

Run: `cd backend && pip install -e ".[dev]" && pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 6: Create `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Gamified Quiz")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run it, expect pass**

Run: `cd backend && pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with health endpoint"
```

---

### Task 2: Database layer (schema + connection)

**Files:**
- Create: `backend/app/db.py`, `backend/tests/test_db.py`

**Interfaces:**
- Produces:
  - `app.db.connect(db_path: str) -> sqlite3.Connection` — returns a connection with `row_factory = sqlite3.Row` and foreign keys ON.
  - `app.db.init_schema(conn: sqlite3.Connection) -> None` — creates all tables if absent (idempotent).
  - Table set (Phase 1): `quizzes`, `questions`, `assets`, `contestants`, `attempts`, `answers`.

- [ ] **Step 1: Write the failing test** in `backend/tests/test_db.py`

```python
import sqlite3
from app.db import connect, init_schema


def test_init_schema_creates_tables(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    names = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "quizzes", "questions", "assets",
        "contestants", "attempts", "answers",
    } <= names


def test_init_schema_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    init_schema(conn)  # must not raise


def test_foreign_keys_enabled(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
```

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Create `backend/app/db.py`**

```python
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS quizzes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT UNIQUE NOT NULL,
    title_ar      TEXT NOT NULL,
    pdf_filename  TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id       INTEGER NOT NULL REFERENCES quizzes(id),
    type          TEXT NOT NULL CHECK (type IN ('mcq','tf','image')),
    prompt_ar     TEXT NOT NULL,
    base_points   INTEGER NOT NULL DEFAULT 100,
    explanation_ar TEXT NOT NULL DEFAULT '',
    source_page   INTEGER,
    data_json     TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id      INTEGER NOT NULL REFERENCES quizzes(id),
    question_id  INTEGER REFERENCES questions(id),
    file_path    TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'image',
    source_url   TEXT NOT NULL DEFAULT '',
    anonymized   INTEGER NOT NULL DEFAULT 0,
    caption_ar   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contestants (
    telegram_user_id INTEGER PRIMARY KEY,
    first_name       TEXT NOT NULL DEFAULT '',
    username         TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    contestant_id    INTEGER NOT NULL REFERENCES contestants(telegram_user_id),
    quiz_id          INTEGER NOT NULL REFERENCES quizzes(id),
    mode             TEXT NOT NULL DEFAULT 'async',
    total_score      INTEGER NOT NULL DEFAULT 0,
    accuracy         REAL NOT NULL DEFAULT 0,
    duration_ms      INTEGER NOT NULL DEFAULT 0,
    started_at       TEXT,
    finished_at      TEXT
);

CREATE TABLE IF NOT EXISTS answers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id    INTEGER NOT NULL REFERENCES attempts(id),
    question_id   INTEGER NOT NULL REFERENCES questions(id),
    given_json    TEXT NOT NULL,
    is_correct    INTEGER NOT NULL,
    time_ms       INTEGER NOT NULL,
    points_awarded INTEGER NOT NULL
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
```

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_db.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/db.py backend/tests/test_db.py
git commit -m "feat: sqlite schema and connection helpers"
```

---

### Task 3: Scoring engine (pure logic, TDD)

**Files:**
- Create: `backend/app/scoring.py`, `backend/tests/test_scoring.py`

**Interfaces:**
- Produces:
  - `app.scoring.clamp_time(time_ms: int) -> int` — clamps to `[0, 60000]`.
  - `app.scoring.speed_bonus(time_ms: int, max_bonus: int = 50, window_ms: int = 60000) -> int` — linear decay: full bonus at 0 ms, 0 at/after `window_ms`.
  - `app.scoring.streak_multiplier(streak: int) -> float` — `1.0 + 0.1 * min(streak, 5)` (caps at 1.5).
  - `app.scoring.score_answer(base_points: int, is_correct: bool, time_ms: int, streak_before: int) -> int` — `0` if wrong; else `round((base + speed_bonus(clamp)) * streak_multiplier(streak_before))`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_scoring.py`

```python
from app.scoring import (
    clamp_time, speed_bonus, streak_multiplier, score_answer,
)


def test_clamp_time_bounds():
    assert clamp_time(-5) == 0
    assert clamp_time(70000) == 60000
    assert clamp_time(1234) == 1234


def test_speed_bonus_decays_linearly():
    assert speed_bonus(0) == 50
    assert speed_bonus(60000) == 0
    assert speed_bonus(30000) == 25


def test_streak_multiplier_caps():
    assert streak_multiplier(0) == 1.0
    assert streak_multiplier(3) == 1.3
    assert streak_multiplier(10) == 1.5


def test_score_answer_wrong_is_zero():
    assert score_answer(100, False, 1000, 4) == 0


def test_score_answer_correct_fast_no_streak():
    # base 100 + bonus 50, multiplier 1.0 -> 150
    assert score_answer(100, True, 0, 0) == 150


def test_score_answer_applies_streak_and_clamp():
    # base 100 + bonus 0 (>=window), multiplier 1.2 -> 120
    assert score_answer(100, True, 90000, 2) == 120
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scoring'`.

- [ ] **Step 3: Create `backend/app/scoring.py`**

```python
def clamp_time(time_ms: int) -> int:
    return max(0, min(int(time_ms), 60000))


def speed_bonus(time_ms: int, max_bonus: int = 50, window_ms: int = 60000) -> int:
    t = clamp_time(time_ms)
    if t >= window_ms:
        return 0
    return round(max_bonus * (1 - t / window_ms))


def streak_multiplier(streak: int) -> float:
    return round(1.0 + 0.1 * min(max(streak, 0), 5), 2)


def score_answer(base_points: int, is_correct: bool, time_ms: int, streak_before: int) -> int:
    if not is_correct:
        return 0
    raw = (base_points + speed_bonus(time_ms)) * streak_multiplier(streak_before)
    return round(raw)
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_scoring.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/scoring.py backend/tests/test_scoring.py
git commit -m "feat: server-authoritative scoring engine"
```

---

### Task 4: Telegram initData validation (TDD)

**Files:**
- Create: `backend/app/auth.py`, `backend/tests/test_auth.py`

**Interfaces:**
- Produces:
  - `app.auth.validate_init_data(init_data: str, bot_token: str) -> dict` — returns parsed fields (incl. a `user` dict) if the HMAC matches; raises `app.auth.AuthError` otherwise.
  - `app.auth.AuthError(Exception)`.
- Algorithm (Telegram WebApp spec): `secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)`, then `expected = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()`, where `data_check_string` is the `\n`-joined sorted `key=value` pairs excluding `hash`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_auth.py`

```python
import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.auth import validate_init_data, AuthError

BOT_TOKEN = "123456:TESTTOKEN"


def _make_init_data(user: dict, token: str = BOT_TOKEN) -> str:
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    data_check_string = "\n".join(
        f"{k}={fields[k]}" for k in sorted(fields)
    )
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


def test_valid_init_data_returns_user():
    raw = _make_init_data({"id": 42, "first_name": "Lina"})
    parsed = validate_init_data(raw, BOT_TOKEN)
    assert parsed["user"]["id"] == 42
    assert parsed["user"]["first_name"] == "Lina"


def test_tampered_hash_rejected():
    raw = _make_init_data({"id": 42, "first_name": "Lina"})
    tampered = raw.replace("Lina", "Evil")
    with pytest.raises(AuthError):
        validate_init_data(tampered, BOT_TOKEN)


def test_missing_hash_rejected():
    with pytest.raises(AuthError):
        validate_init_data("auth_date=1700000000", BOT_TOKEN)
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`.

- [ ] **Step 3: Create `backend/app/auth.py`**

```python
import hashlib
import hmac
import json
from urllib.parse import parse_qsl


class AuthError(Exception):
    pass


def validate_init_data(init_data: str, bot_token: str) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise AuthError("missing hash")

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise AuthError("hash mismatch")

    if "user" in pairs:
        pairs["user"] = json.loads(pairs["user"])
    return pairs
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth.py backend/tests/test_auth.py
git commit -m "feat: validate Telegram initData HMAC"
```

---

### Task 5: Question-bank schema validation (TDD)

**Files:**
- Create: `backend/app/content_schema.py`, `backend/tests/test_content_schema.py`

**Interfaces:**
- Produces:
  - `app.content_schema.SchemaError(Exception)`.
  - `app.content_schema.validate_quiz(doc: dict) -> None` — raises `SchemaError` if invalid.
- Expected quiz-bank document shape:

```json
{
  "slug": "journals",
  "title_ar": "تصنيف المجلات العلمية",
  "pdf_filename": "المحور الثاني -تصنيف المجلات العلمية.pdf",
  "questions": [
    {
      "type": "mcq",
      "prompt_ar": "...",
      "base_points": 100,
      "explanation_ar": "...",
      "source_page": 5,
      "options_ar": ["...", "...", "...", "..."],
      "correct_index": 2,
      "asset": {"file": "assets/journals/x.png", "source_url": "https://...", "anonymized": true, "caption_ar": "..."}
    }
  ]
}
```

Rules: `slug`, `title_ar`, `pdf_filename`, `questions` required. Each question needs `type ∈ {mcq,tf,image}`, non-empty `prompt_ar`, `options_ar` (≥2 for mcq/image; exactly 2 for tf), integer `correct_index` in range. `asset` required for `image`, optional otherwise; when present, `file` and `source_url` required.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_content_schema.py`

```python
import pytest
from app.content_schema import validate_quiz, SchemaError


def _good_doc():
    return {
        "slug": "journals",
        "title_ar": "تصنيف",
        "pdf_filename": "x.pdf",
        "questions": [
            {
                "type": "mcq",
                "prompt_ar": "سؤال",
                "options_ar": ["أ", "ب", "ج", "د"],
                "correct_index": 1,
            },
            {
                "type": "image",
                "prompt_ar": "أيهما حقيقي؟",
                "options_ar": ["اليسار", "اليمين"],
                "correct_index": 0,
                "asset": {"file": "assets/journals/a.png", "source_url": "https://e.x/a"},
            },
        ],
    }


def test_valid_doc_passes():
    validate_quiz(_good_doc())  # must not raise


def test_missing_slug_fails():
    doc = _good_doc()
    del doc["slug"]
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_correct_index_out_of_range_fails():
    doc = _good_doc()
    doc["questions"][0]["correct_index"] = 9
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_image_without_asset_fails():
    doc = _good_doc()
    del doc["questions"][1]["asset"]
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_tf_must_have_two_options():
    doc = _good_doc()
    doc["questions"].append(
        {"type": "tf", "prompt_ar": "صح؟", "options_ar": ["صح"], "correct_index": 0}
    )
    with pytest.raises(SchemaError):
        validate_quiz(doc)
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_content_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.content_schema'`.

- [ ] **Step 3: Create `backend/app/content_schema.py`**

```python
class SchemaError(Exception):
    pass


VALID_TYPES = {"mcq", "tf", "image"}


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def validate_quiz(doc: dict) -> None:
    for key in ("slug", "title_ar", "pdf_filename", "questions"):
        _require(key in doc and doc[key], f"missing field: {key}")
    _require(isinstance(doc["questions"], list) and doc["questions"], "questions must be a non-empty list")

    for i, q in enumerate(doc["questions"]):
        where = f"question[{i}]"
        _require(q.get("type") in VALID_TYPES, f"{where}: bad type {q.get('type')!r}")
        _require(bool(q.get("prompt_ar")), f"{where}: empty prompt_ar")

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
        if "asset" in q:
            a = q["asset"]
            _require(bool(a.get("file")), f"{where}: asset.file required")
            _require(bool(a.get("source_url")), f"{where}: asset.source_url required")
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_content_schema.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/content_schema.py backend/tests/test_content_schema.py
git commit -m "feat: question-bank schema validation"
```

---

### Task 6: Repository functions + seed loader (TDD)

**Files:**
- Create: `backend/app/models.py`, `backend/app/seed.py`, `backend/tests/conftest.py`, `backend/tests/test_seed.py`

**Interfaces:**
- Consumes: `app.db.connect`, `app.db.init_schema`, `app.content_schema.validate_quiz`.
- Produces (`app.models`):
  - `upsert_contestant(conn, user: dict) -> int` — inserts/updates a contestant from a Telegram `user` dict, returns `telegram_user_id`.
  - `get_quiz_by_slug(conn, slug: str) -> sqlite3.Row | None`.
  - `get_questions(conn, quiz_id: int) -> list[sqlite3.Row]` — ordered by `display_order`.
  - `get_asset_for_question(conn, question_id: int) -> sqlite3.Row | None`.
  - `create_attempt(conn, contestant_id, quiz_id, mode, started_at) -> int`.
  - `finish_attempt(conn, attempt_id, total_score, accuracy, duration_ms, finished_at) -> None`.
  - `record_answer(conn, attempt_id, question_id, given, is_correct, time_ms, points) -> None`.
  - `leaderboard(conn, quiz_id, limit=20) -> list[sqlite3.Row]` — best `total_score` per contestant, descending; columns `first_name, best_score`.
- Produces (`app.seed`): `seed_quiz(conn, doc: dict) -> int` — validates then inserts quiz + questions + assets (idempotent on `slug`: deletes existing quiz rows first), returns `quiz_id`. `seed_from_file(conn, path: str) -> int`.

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
import json
import pytest
from app.db import connect, init_schema
from app.seed import seed_quiz


SAMPLE_DOC = {
    "slug": "journals",
    "title_ar": "تصنيف المجلات",
    "pdf_filename": "x.pdf",
    "questions": [
        {
            "type": "mcq",
            "prompt_ar": "سؤال 1",
            "base_points": 100,
            "explanation_ar": "شرح 1",
            "source_page": 3,
            "options_ar": ["أ", "ب", "ج", "د"],
            "correct_index": 2,
        },
        {
            "type": "image",
            "prompt_ar": "أيهما حقيقي؟",
            "base_points": 100,
            "explanation_ar": "شرح 2",
            "source_page": 5,
            "options_ar": ["اليسار", "اليمين"],
            "correct_index": 0,
            "asset": {
                "file": "assets/journals/compare.png",
                "source_url": "https://example.org/compare",
                "anonymized": True,
                "caption_ar": "بريدان",
            },
        },
    ],
}


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def seeded(conn):
    quiz_id = seed_quiz(conn, SAMPLE_DOC)
    return conn, quiz_id
```

- [ ] **Step 2: Write the failing tests** in `backend/tests/test_seed.py`

```python
from app.models import get_quiz_by_slug, get_questions, get_asset_for_question
from app.seed import seed_quiz
from tests.conftest import SAMPLE_DOC


def test_seed_inserts_quiz_and_questions(seeded):
    conn, quiz_id = seeded
    quiz = get_quiz_by_slug(conn, "journals")
    assert quiz["id"] == quiz_id
    questions = get_questions(conn, quiz_id)
    assert len(questions) == 2
    assert questions[0]["prompt_ar"] == "سؤال 1"


def test_seed_attaches_asset_to_image_question(seeded):
    conn, quiz_id = seeded
    image_q = get_questions(conn, quiz_id)[1]
    asset = get_asset_for_question(conn, image_q["id"])
    assert asset is not None
    assert asset["file_path"] == "assets/journals/compare.png"


def test_seed_is_idempotent(conn):
    seed_quiz(conn, SAMPLE_DOC)
    seed_quiz(conn, SAMPLE_DOC)
    assert len(get_questions(conn, get_quiz_by_slug(conn, "journals")["id"])) == 2
```

- [ ] **Step 3: Run them, expect failure**

Run: `cd backend && pytest tests/test_seed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 4: Create `backend/app/models.py`**

```python
import json
import sqlite3


def upsert_contestant(conn: sqlite3.Connection, user: dict) -> int:
    uid = int(user["id"])
    conn.execute(
        """
        INSERT INTO contestants (telegram_user_id, first_name, username, created_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(telegram_user_id) DO UPDATE SET
            first_name = excluded.first_name,
            username   = excluded.username
        """,
        (uid, user.get("first_name", ""), user.get("username")),
    )
    conn.commit()
    return uid


def get_quiz_by_slug(conn, slug):
    return conn.execute("SELECT * FROM quizzes WHERE slug = ?", (slug,)).fetchone()


def get_questions(conn, quiz_id):
    return conn.execute(
        "SELECT * FROM questions WHERE quiz_id = ? ORDER BY display_order, id",
        (quiz_id,),
    ).fetchall()


def get_asset_for_question(conn, question_id):
    return conn.execute(
        "SELECT * FROM assets WHERE question_id = ? LIMIT 1", (question_id,)
    ).fetchone()


def create_attempt(conn, contestant_id, quiz_id, mode, started_at):
    cur = conn.execute(
        "INSERT INTO attempts (contestant_id, quiz_id, mode, started_at) VALUES (?, ?, ?, ?)",
        (contestant_id, quiz_id, mode, started_at),
    )
    conn.commit()
    return cur.lastrowid


def finish_attempt(conn, attempt_id, total_score, accuracy, duration_ms, finished_at):
    conn.execute(
        """UPDATE attempts SET total_score=?, accuracy=?, duration_ms=?, finished_at=?
           WHERE id=?""",
        (total_score, accuracy, duration_ms, finished_at, attempt_id),
    )
    conn.commit()


def record_answer(conn, attempt_id, question_id, given, is_correct, time_ms, points):
    conn.execute(
        """INSERT INTO answers
           (attempt_id, question_id, given_json, is_correct, time_ms, points_awarded)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (attempt_id, question_id, json.dumps(given), int(is_correct), time_ms, points),
    )
    conn.commit()


def leaderboard(conn, quiz_id, limit=20):
    return conn.execute(
        """
        SELECT c.first_name AS first_name, MAX(a.total_score) AS best_score
        FROM attempts a
        JOIN contestants c ON c.telegram_user_id = a.contestant_id
        WHERE a.quiz_id = ? AND a.finished_at IS NOT NULL
        GROUP BY a.contestant_id
        ORDER BY best_score DESC
        LIMIT ?
        """,
        (quiz_id, limit),
    ).fetchall()
```

- [ ] **Step 5: Create `backend/app/seed.py`**

```python
import json
import sqlite3

from app.content_schema import validate_quiz


def seed_quiz(conn: sqlite3.Connection, doc: dict) -> int:
    validate_quiz(doc)

    existing = conn.execute(
        "SELECT id FROM quizzes WHERE slug = ?", (doc["slug"],)
    ).fetchone()
    if existing:
        qid = existing["id"]
        conn.execute("DELETE FROM assets WHERE quiz_id = ?", (qid,))
        conn.execute("DELETE FROM questions WHERE quiz_id = ?", (qid,))
        conn.execute("DELETE FROM quizzes WHERE id = ?", (qid,))

    cur = conn.execute(
        "INSERT INTO quizzes (slug, title_ar, pdf_filename, display_order) VALUES (?, ?, ?, ?)",
        (doc["slug"], doc["title_ar"], doc["pdf_filename"], doc.get("display_order", 0)),
    )
    quiz_id = cur.lastrowid

    for order, q in enumerate(doc["questions"]):
        data = {"options_ar": q["options_ar"], "correct_index": q["correct_index"]}
        qcur = conn.execute(
            """INSERT INTO questions
               (quiz_id, type, prompt_ar, base_points, explanation_ar, source_page, data_json, display_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                quiz_id, q["type"], q["prompt_ar"], q.get("base_points", 100),
                q.get("explanation_ar", ""), q.get("source_page"),
                json.dumps(data, ensure_ascii=False), order,
            ),
        )
        question_id = qcur.lastrowid
        if "asset" in q:
            a = q["asset"]
            conn.execute(
                """INSERT INTO assets
                   (quiz_id, question_id, file_path, kind, source_url, anonymized, caption_ar)
                   VALUES (?, ?, ?, 'image', ?, ?, ?)""",
                (
                    quiz_id, question_id, a["file"], a["source_url"],
                    int(a.get("anonymized", False)), a.get("caption_ar", ""),
                ),
            )
    conn.commit()
    return quiz_id


def seed_from_file(conn: sqlite3.Connection, path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return seed_quiz(conn, json.load(f))
```

- [ ] **Step 6: Run the tests, expect pass**

Run: `cd backend && pytest tests/test_seed.py -v`
Expected: PASS (3 passed).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models.py backend/app/seed.py backend/tests/conftest.py backend/tests/test_seed.py
git commit -m "feat: repository functions and seed loader"
```

---

### Task 7: Report builder (TDD)

**Files:**
- Create: `backend/app/report.py`, `backend/tests/test_report.py`

**Interfaces:**
- Consumes: `app.models` rows.
- Produces:
  - `app.report.build_report(conn, attempt_id: int) -> dict` — returns
    `{"total_score", "accuracy", "duration_ms", "rank", "items": [ {prompt_ar, given_index, correct_index, is_correct, explanation_ar, source_page, asset_file, options_ar} ]}`.
  - `app.report.format_report_text(report: dict, title_ar: str) -> str` — Arabic plain-text summary for the bot DM (score, accuracy %, rank, count correct).

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_report.py`

```python
import json
from app.models import upsert_contestant, create_attempt, finish_attempt, record_answer, get_questions, get_quiz_by_slug
from app.report import build_report, format_report_text


def _seed_attempt(conn, quiz_id):
    uid = upsert_contestant(conn, {"id": 7, "first_name": "Sara"})
    attempt_id = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    questions = get_questions(conn, quiz_id)
    record_answer(conn, attempt_id, questions[0]["id"], {"index": 2}, True, 1000, 150)
    record_answer(conn, attempt_id, questions[1]["id"], {"index": 1}, False, 2000, 0)
    finish_attempt(conn, attempt_id, 150, 0.5, 3000, "2026-06-25T10:00:05")
    return attempt_id


def test_build_report_shape(seeded):
    conn, quiz_id = seeded
    attempt_id = _seed_attempt(conn, quiz_id)
    report = build_report(conn, attempt_id)
    assert report["total_score"] == 150
    assert report["accuracy"] == 0.5
    assert len(report["items"]) == 2
    first = report["items"][0]
    assert first["is_correct"] is True
    assert first["correct_index"] == 2
    assert first["given_index"] == 2


def test_build_report_includes_asset_for_image(seeded):
    conn, quiz_id = seeded
    attempt_id = _seed_attempt(conn, quiz_id)
    report = build_report(conn, attempt_id)
    assert report["items"][1]["asset_file"] == "assets/journals/compare.png"


def test_format_report_text_is_arabic_summary(seeded):
    conn, quiz_id = seeded
    attempt_id = _seed_attempt(conn, quiz_id)
    report = build_report(conn, attempt_id)
    text = format_report_text(report, "تصنيف المجلات")
    assert "150" in text
    assert "تصنيف المجلات" in text
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.report'`.

- [ ] **Step 3: Create `backend/app/report.py`**

```python
import json


def build_report(conn, attempt_id: int) -> dict:
    attempt = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    answers = conn.execute(
        "SELECT * FROM answers WHERE attempt_id = ? ORDER BY id", (attempt_id,)
    ).fetchall()

    items = []
    for ans in answers:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (ans["question_id"],)).fetchone()
        data = json.loads(q["data_json"])
        asset = conn.execute(
            "SELECT file_path FROM assets WHERE question_id = ? LIMIT 1", (q["id"],)
        ).fetchone()
        items.append({
            "prompt_ar": q["prompt_ar"],
            "options_ar": data["options_ar"],
            "correct_index": data["correct_index"],
            "given_index": json.loads(ans["given_json"]).get("index"),
            "is_correct": bool(ans["is_correct"]),
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

    return {
        "total_score": attempt["total_score"],
        "accuracy": attempt["accuracy"],
        "duration_ms": attempt["duration_ms"],
        "rank": rank_row["rank"],
        "items": items,
    }


def format_report_text(report: dict, title_ar: str) -> str:
    correct = sum(1 for it in report["items"] if it["is_correct"])
    total = len(report["items"])
    pct = round(report["accuracy"] * 100)
    return (
        f"🏁 نتيجتك في: {title_ar}\n"
        f"النقاط: {report['total_score']}\n"
        f"الإجابات الصحيحة: {correct}/{total} ({pct}%)\n"
        f"الترتيب: #{report['rank']}"
    )
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_report.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/report.py backend/tests/test_report.py
git commit -m "feat: per-attempt report builder and bot summary text"
```

---

### Task 8: REST API (questions, submit, leaderboard)

**Files:**
- Create: `backend/app/api.py`
- Modify: `backend/app/main.py` (mount the API router + a DB dependency), `backend/tests/test_api.py` (add API tests)

**Interfaces:**
- Consumes: `app.auth.validate_init_data`, `app.models.*`, `app.scoring.score_answer`, `app.report.build_report`, `app.config.settings`.
- Produces these routes (all under the app):
  - `GET /api/quizzes` → `[{slug, title_ar}]`.
  - `GET /api/quizzes/{slug}/questions` → `{quiz: {slug,title_ar}, questions: [{id, type, prompt_ar, options_ar, asset_file, base_points}]}` (no `correct_index` leaked).
  - `POST /api/quizzes/{slug}/submit` with header `X-Init-Data` and body `{"answers": [{"question_id", "index", "time_ms"}], "duration_ms": int}` → the report dict (adds `attempt_id`). Server resolves correctness, scores, persists attempt + answers.
  - `GET /api/leaderboard?slug=` → `[{first_name, best_score}]`.
- DB access: `app.main` opens one shared connection at startup (`check_same_thread=False`) and `api.py` reads it via a module-level accessor `get_conn()`.

- [ ] **Step 1: Add the failing API tests** to `backend/tests/test_api.py` (append below the existing health test)

```python
import json
import hashlib, hmac
from urllib.parse import urlencode

import pytest
from app import main as main_module
from app.db import connect, init_schema
from app.seed import seed_quiz
from tests.conftest import SAMPLE_DOC

BOT_TOKEN = "123456:TESTTOKEN"


def _init_data(user):
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "api.db")
    conn = connect(db_file)
    init_schema(conn)
    seed_quiz(conn, SAMPLE_DOC)
    monkeypatch.setattr(main_module, "_conn", conn, raising=False)
    monkeypatch.setattr(main_module.settings, "bot_token", BOT_TOKEN, raising=False)
    from fastapi.testclient import TestClient
    return TestClient(main_module.app)


def test_list_quizzes(api_client):
    resp = api_client.get("/api/quizzes")
    assert resp.status_code == 200
    assert resp.json()[0]["slug"] == "journals"


def test_get_questions_hides_correct_index(api_client):
    resp = api_client.get("/api/quizzes/journals/questions")
    body = resp.json()
    assert len(body["questions"]) == 2
    assert "correct_index" not in body["questions"][0]


def test_submit_scores_and_returns_report(api_client):
    init = _init_data({"id": 99, "first_name": "Omar"})
    questions = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    answers = [
        {"question_id": questions[0]["id"], "index": 2, "time_ms": 1000},
        {"question_id": questions[1]["id"], "index": 0, "time_ms": 1500},
    ]
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": answers, "duration_ms": 2500},
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["total_score"] > 0
    assert len(report["items"]) == 2
    assert all(it["is_correct"] for it in report["items"])


def test_submit_rejects_bad_initdata(api_client):
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": "auth_date=1&hash=deadbeef"},
        json={"answers": [], "duration_ms": 0},
    )
    assert resp.status_code == 401


def test_leaderboard_after_submit(api_client):
    init = _init_data({"id": 99, "first_name": "Omar"})
    questions = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": [{"question_id": questions[0]["id"], "index": 2, "time_ms": 500}], "duration_ms": 500},
    )
    board = api_client.get("/api/leaderboard?slug=journals").json()
    assert board[0]["first_name"] == "Omar"
    assert board[0]["best_score"] > 0
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_api.py -v`
Expected: FAIL — submit/quizzes routes return 404 (not yet defined).

- [ ] **Step 3: Create `backend/app/api.py`**

```python
import json

from fastapi import APIRouter, Header, HTTPException, Request

from app import models
from app.auth import validate_init_data, AuthError
from app.config import settings
from app.scoring import score_answer

router = APIRouter(prefix="/api")


def _conn(request: Request):
    conn = getattr(request.app.state, "conn", None)
    if conn is None:
        from app.main import _conn as shared  # set at startup
        conn = shared
    return conn


@router.get("/quizzes")
def list_quizzes(request: Request):
    conn = _conn(request)
    rows = conn.execute("SELECT slug, title_ar FROM quizzes ORDER BY display_order, id").fetchall()
    return [{"slug": r["slug"], "title_ar": r["title_ar"]} for r in rows]


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
        out.append({
            "id": q["id"],
            "type": q["type"],
            "prompt_ar": q["prompt_ar"],
            "options_ar": data["options_ar"],
            "base_points": q["base_points"],
            "asset_file": asset["file_path"] if asset else None,
        })
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]}, "questions": out}


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

    correct_by_id = {}
    base_by_id = {}
    for q in models.get_questions(conn, quiz["id"]):
        correct_by_id[q["id"]] = json.loads(q["data_json"])["correct_index"]
        base_by_id[q["id"]] = q["base_points"]

    contestant_id = models.upsert_contestant(conn, user)
    attempt_id = models.create_attempt(conn, contestant_id, quiz["id"], "async", _now(conn))

    total = 0
    correct_count = 0
    streak = 0
    answers = payload.get("answers", [])
    for a in answers:
        qid = a["question_id"]
        if qid not in correct_by_id:
            continue
        is_correct = int(a.get("index")) == correct_by_id[qid]
        pts = score_answer(base_by_id[qid], is_correct, int(a.get("time_ms", 60000)), streak)
        streak = streak + 1 if is_correct else 0
        if is_correct:
            correct_count += 1
        total += pts
        models.record_answer(conn, attempt_id, qid, {"index": a.get("index")}, is_correct, int(a.get("time_ms", 0)), pts)

    accuracy = correct_count / len(answers) if answers else 0.0
    models.finish_attempt(conn, attempt_id, total, accuracy, int(payload.get("duration_ms", 0)), _now(conn))

    from app.report import build_report
    report = build_report(conn, attempt_id)
    report["attempt_id"] = attempt_id
    return report


@router.get("/leaderboard")
def get_leaderboard(slug: str, request: Request):
    conn = _conn(request)
    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")
    rows = models.leaderboard(conn, quiz["id"])
    return [{"first_name": r["first_name"], "best_score": r["best_score"]} for r in rows]


def _now(conn):
    return conn.execute("SELECT datetime('now')").fetchone()[0]
```

- [ ] **Step 4: Update `backend/app/main.py`** to open the shared connection, expose it as `_conn`, mount the router and static frontend

```python
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import connect, init_schema

app = FastAPI(title="Gamified Quiz")

_conn = connect(settings.db_path) if False else None  # set in startup for prod


@app.on_event("startup")
def _startup():
    global _conn
    if _conn is None:
        import sqlite3
        conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        init_schema(conn)
        _conn = conn
    app.state.conn = _conn


@app.get("/health")
def health():
    return {"status": "ok"}


from app.api import router as api_router  # noqa: E402
app.include_router(api_router)

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="app")

_content_dir = os.path.join(os.path.dirname(__file__), "..", "..", "content")
if os.path.isdir(_content_dir):
    app.mount("/content", StaticFiles(directory=_content_dir), name="content")
```

Note: in `api.py`, `_conn(request)` first reads `request.app.state.conn` (set at startup and overridable in tests by setting `main._conn` + `app.state.conn`). For the test fixture, also set `app.state.conn`:

- [ ] **Step 5: Fix the test fixture** so `app.state.conn` is set — update `api_client` in `backend/tests/test_api.py`:

```python
    monkeypatch.setattr(main_module, "_conn", conn, raising=False)
    main_module.app.state.conn = conn
    monkeypatch.setattr(main_module.settings, "bot_token", BOT_TOKEN, raising=False)
```

- [ ] **Step 6: Run all API tests, expect pass**

Run: `cd backend && pytest tests/test_api.py -v`
Expected: PASS (health + 5 API tests).

- [ ] **Step 7: Run the full suite**

Run: `cd backend && pytest -v`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api.py backend/app/main.py backend/tests/test_api.py
git commit -m "feat: REST API for questions, scored submit, leaderboard"
```

---

### Task 9: PDF extraction script + curated journals content

**Files:**
- Create: `scripts/extract.py`, `content/questions/journals.json`, `content/assets/journals/` (real screenshots)

**Interfaces:**
- Produces: `scripts/extract.py` CLI — `python scripts/extract.py "<pdf path>" content/raw/journals.txt`. Uses `pdftotext`.
- Produces: a curated, schema-valid `content/questions/journals.json` with **≥6 questions** (mix of `mcq`, `tf`, `image`) grounded in the journals PDF, each real `image` question referencing a downloaded artifact in `content/assets/journals/`.

- [ ] **Step 1: Create `scripts/extract.py`**

```python
import subprocess
import sys


def extract(pdf_path: str, out_path: str) -> None:
    subprocess.run(["pdftotext", pdf_path, out_path], check=True)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: extract.py <pdf> <out.txt>")
        raise SystemExit(2)
    extract(sys.argv[1], sys.argv[2])
```

- [ ] **Step 2: Extract the journals PDF text**

Run:
```bash
mkdir -p content/raw content/assets/journals
python scripts/extract.py "المحور الثاني -تصنيف المجلات العلمية.pdf" content/raw/journals.txt
```
Expected: `content/raw/journals.txt` exists and is non-empty.

- [ ] **Step 3: Read the extracted text and identify ≥6 teaching points.**

Read `content/raw/journals.txt`. Note the concepts that have a real-world artifact (predatory vs. legitimate journal emails; indexing/quartile badges; database search filters; APC/fee red flags). For each, decide the question type.

- [ ] **Step 4: Source real artifacts for the `image` questions.**

For each image question, find a **genuine public** screenshot (real predatory-journal solicitation email; a real DOAJ / Scimago / journal "find a journal" filter view). Verify sandbox network access first:
```bash
python -c "import urllib.request; urllib.request.urlopen('https://doaj.org', timeout=10); print('network ok')"
```
- If network OK: download into `content/assets/journals/` (e.g. `predatory_vs_legit.png`, `doaj_filters.png`), **anonymize** any personal names/emails (blur), and record each `source_url` in the question's `asset` block.
- If network blocked: STOP and ask the user to drop the real screenshots into `content/assets/journals/` and provide their source URLs. Do not fabricate artifacts.

- [ ] **Step 5: Write `content/questions/journals.json`** — schema-valid, ≥6 questions. Example skeleton (replace prompts/options/assets with real curated content):

```json
{
  "slug": "journals",
  "title_ar": "تصنيف المجلات العلمية",
  "pdf_filename": "المحور الثاني -تصنيف المجلات العلمية.pdf",
  "display_order": 1,
  "questions": [
    {
      "type": "image",
      "prompt_ar": "أمامك رسالتان من مجلتين. أيّهما مجلة محترِسة (predatory)؟",
      "base_points": 120,
      "explanation_ar": "الرسالة اليمنى تَعِد بقبول خلال 48 ساعة ورسوم فورية — علامات مجلة محترِسة.",
      "source_page": 8,
      "options_ar": ["الرسالة اليسرى", "الرسالة اليمنى"],
      "correct_index": 1,
      "asset": {
        "file": "assets/journals/predatory_vs_legit.png",
        "source_url": "https://REAL-SOURCE-URL",
        "anonymized": true,
        "caption_ar": "مقارنة بين بريدين حقيقيين"
      }
    },
    {
      "type": "mcq",
      "prompt_ar": "أي مؤشر يدل على جودة المجلة وتصنيفها ضمن الربع الأول (Q1)؟",
      "base_points": 100,
      "explanation_ar": "تصنيف الأرباع (Quartiles) يعتمد على معامل التأثير ضمن مجال التخصص.",
      "source_page": 5,
      "options_ar": ["عدد الإعلانات", "معامل التأثير والاقتباسات", "سرعة القبول", "رسوم النشر"],
      "correct_index": 1
    },
    {
      "type": "tf",
      "prompt_ar": "وجود رقم ISSN وحده يضمن أن المجلة ليست محترِسة.",
      "base_points": 80,
      "explanation_ar": "خطأ — المجلات المحترِسة قد تمتلك ISSN أيضًا؛ يجب التحقق من الفهرسة والناشر.",
      "source_page": 9,
      "options_ar": ["صحيح", "خطأ"],
      "correct_index": 1
    }
  ]
}
```

- [ ] **Step 6: Validate the curated file** (no DB needed)

Run:
```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/journals.json', encoding='utf-8'))); print('valid')"
```
Expected: `valid`.

- [ ] **Step 7: Seed a local DB from the file and sanity-check**

Run:
```bash
cd backend && python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_from_file; c=connect('../quiz.db'); init_schema(c); qid=seed_from_file(c,'../content/questions/journals.json'); print('seeded quiz', qid, 'questions', len(c.execute('select * from questions').fetchall()))"
```
Expected: prints a quiz id and the question count (≥6).

- [ ] **Step 8: Commit** (content + script; `content/raw/` is gitignored)

```bash
git add scripts/extract.py content/questions/journals.json content/assets/journals/
git commit -m "feat: extraction script and curated journals quiz with real artifacts"
```

---

### Task 10: Mini App frontend (RTL: home → runner → report → leaderboard)

**Files:**
- Create: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`

**Interfaces:**
- Consumes the REST API (`/api/quizzes`, `/api/quizzes/{slug}/questions`, `/api/quizzes/{slug}/submit`, `/api/leaderboard`) and serves the `X-Init-Data` header from `Telegram.WebApp.initData`. Image assets load from `/content/<asset_file>`.
- No automated tests (UI); verified by the manual checklist in Task 12.

- [ ] **Step 1: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>مسابقة المجلات العلمية</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <main id="app">
    <section id="screen-home" class="screen">
      <h1>مسابقة الجلسات</h1>
      <div id="quiz-list"></div>
    </section>

    <section id="screen-runner" class="screen hidden">
      <div class="topbar">
        <span id="progress"></span>
        <span id="timer">0.0s</span>
      </div>
      <h2 id="q-prompt"></h2>
      <img id="q-image" class="q-image hidden" alt="" />
      <div id="q-options"></div>
    </section>

    <section id="screen-report" class="screen hidden">
      <h2>نتيجتك</h2>
      <div id="report-summary"></div>
      <div id="report-items"></div>
      <button id="btn-board">عرض لوحة الصدارة</button>
    </section>

    <section id="screen-board" class="screen hidden">
      <h2>لوحة الصدارة</h2>
      <ol id="board-list"></ol>
      <button id="btn-home">العودة</button>
    </section>
  </main>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `frontend/styles.css`**

```css
:root { --bg:#0f1115; --card:#1b2030; --accent:#4f8cff; --good:#2fbf71; --bad:#e0524f; --fg:#f3f5f9; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, "Segoe UI", Tahoma, sans-serif; background:var(--bg); color:var(--fg); }
#app { max-width: 560px; margin: 0 auto; padding: 16px; }
.screen { animation: fade .2s ease; }
.hidden { display:none; }
@keyframes fade { from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;} }
h1,h2 { text-align:center; }
.topbar { display:flex; justify-content:space-between; font-variant-numeric: tabular-nums; color:#9aa4bf; }
.q-image { width:100%; border-radius:12px; margin:12px 0; }
button, .opt {
  display:block; width:100%; margin:8px 0; padding:14px; border:none; border-radius:12px;
  background:var(--card); color:var(--fg); font-size:1rem; cursor:pointer; text-align:right;
}
.opt.good { background:var(--good); } .opt.bad { background:var(--bad); }
#btn-board, #btn-home, .quiz-card { background:var(--accent); text-align:center; font-weight:600; }
.summary-big { font-size:2rem; text-align:center; margin:8px 0; }
.report-item { background:var(--card); border-radius:12px; padding:12px; margin:8px 0; }
.report-item.good { border-right:4px solid var(--good); }
.report-item.bad { border-right:4px solid var(--bad); }
.report-item img { width:100%; border-radius:8px; margin-top:8px; }
ol#board-list li { background:var(--card); margin:6px 0; padding:10px; border-radius:10px; }
```

- [ ] **Step 3: Create `frontend/app.js`**

```javascript
const tg = window.Telegram ? window.Telegram.WebApp : { initData: "", ready() {}, expand() {} };
tg.ready(); tg.expand();

const screens = ["home", "runner", "report", "board"];
function show(name) {
  screens.forEach(s => document.getElementById("screen-" + s).classList.toggle("hidden", s !== name));
}

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts);
  if (!res.ok) throw new Error("api " + res.status);
  return res.json();
}

let state = { slug: null, questions: [], idx: 0, answers: [], qStart: 0, timer: null };

async function loadHome() {
  const quizzes = await api("/quizzes");
  const list = document.getElementById("quiz-list");
  list.innerHTML = "";
  quizzes.forEach(q => {
    const b = document.createElement("button");
    b.className = "quiz-card";
    b.textContent = q.title_ar;
    b.onclick = () => startQuiz(q.slug);
    list.appendChild(b);
  });
  show("home");
}

async function startQuiz(slug) {
  const data = await api(`/quizzes/${slug}/questions`);
  state = { slug, questions: data.questions, idx: 0, answers: [], qStart: 0, timer: null, startedAt: Date.now() };
  renderQuestion();
  show("runner");
}

function renderQuestion() {
  const q = state.questions[state.idx];
  document.getElementById("progress").textContent = `${state.idx + 1}/${state.questions.length}`;
  document.getElementById("q-prompt").textContent = q.prompt_ar;
  const img = document.getElementById("q-image");
  if (q.asset_file) { img.src = "/content/" + q.asset_file; img.classList.remove("hidden"); }
  else { img.classList.add("hidden"); img.removeAttribute("src"); }

  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  q.options_ar.forEach((text, i) => {
    const btn = document.createElement("button");
    btn.className = "opt";
    btn.textContent = text;
    btn.onclick = () => answer(i);
    opts.appendChild(btn);
  });

  state.qStart = Date.now();
  const timerEl = document.getElementById("timer");
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    timerEl.textContent = ((Date.now() - state.qStart) / 1000).toFixed(1) + "s";
  }, 100);
}

function answer(index) {
  clearInterval(state.timer);
  const q = state.questions[state.idx];
  state.answers.push({ question_id: q.id, index, time_ms: Date.now() - state.qStart });
  state.idx += 1;
  if (state.idx < state.questions.length) renderQuestion();
  else submit();
}

async function submit() {
  const report = await api(`/quizzes/${state.slug}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData },
    body: JSON.stringify({ answers: state.answers, duration_ms: Date.now() - state.startedAt }),
  });
  renderReport(report);
  show("report");
}

function renderReport(report) {
  const correct = report.items.filter(i => i.is_correct).length;
  document.getElementById("report-summary").innerHTML =
    `<div class="summary-big">${report.total_score} نقطة</div>` +
    `<div style="text-align:center">صحيح ${correct}/${report.items.length} — الترتيب #${report.rank}</div>`;
  const box = document.getElementById("report-items");
  box.innerHTML = "";
  report.items.forEach(it => {
    const div = document.createElement("div");
    div.className = "report-item " + (it.is_correct ? "good" : "bad");
    const yours = it.options_ar[it.given_index] ?? "—";
    const right = it.options_ar[it.correct_index];
    div.innerHTML =
      `<div>${it.prompt_ar}</div>` +
      `<div>إجابتك: ${yours} ${it.is_correct ? "✅" : "❌"}</div>` +
      (it.is_correct ? "" : `<div>الصحيح: ${right}</div>`) +
      (it.explanation_ar ? `<div>📖 ${it.explanation_ar}` + (it.source_page ? ` (ص ${it.source_page})` : "") + `</div>` : "") +
      (it.asset_file ? `<img src="/content/${it.asset_file}" alt="" />` : "");
    box.appendChild(div);
  });
  document.getElementById("btn-board").onclick = () => loadBoard();
}

async function loadBoard() {
  const board = await api(`/leaderboard?slug=${state.slug}`);
  const ol = document.getElementById("board-list");
  ol.innerHTML = "";
  board.forEach(r => {
    const li = document.createElement("li");
    li.textContent = `${r.first_name} — ${r.best_score}`;
    ol.appendChild(li);
  });
  document.getElementById("btn-home").onclick = loadHome;
  show("board");
}

loadHome().catch(e => { document.getElementById("quiz-list").textContent = "تعذّر التحميل"; });
```

- [ ] **Step 4: Manual smoke test in a browser** (Telegram not required for layout)

Run:
```bash
cd backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --reload --port 8000
```
Open `http://localhost:8000/app/`. Expected: RTL home screen lists the "تصنيف المجلات العلمية" quiz; clicking it shows questions with images; finishing shows a report; the board button shows a leaderboard. (Submit will 401 outside Telegram because `initData` is empty — that's expected here; full submit is verified in Task 12 inside Telegram.)

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: RTL Mini App (home, runner, report, leaderboard)"
```

---

### Task 11: Telegram bot (entry point, report DM, leaderboard command)

**Files:**
- Create: `backend/app/bot.py`
- Modify: `backend/tests/test_report.py` is unaffected; add `backend/tests/test_bot.py` for the pure formatting wiring.

**Interfaces:**
- Consumes: `app.config.settings`, `app.db`, `app.models.leaderboard`, `app.report.format_report_text`.
- Produces:
  - `app.bot.build_application()` → a configured `telegram.ext.Application` with handlers for `/start`, `/leaderboard`.
  - `app.bot.leaderboard_text(conn, slug) -> str` — pure Arabic text of the top board (testable without Telegram).
  - `/start` replies with an inline button (`WebAppInfo`) opening `settings.public_url + "/app/"`.

- [ ] **Step 1: Write the failing test** in `backend/tests/test_bot.py`

```python
from app.bot import leaderboard_text
from app.models import upsert_contestant, create_attempt, finish_attempt


def test_leaderboard_text_lists_names(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 5, "first_name": "Nour"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    finish_attempt(conn, aid, 240, 1.0, 4000, "2026-06-25T10:00:04")
    text = leaderboard_text(conn, "journals")
    assert "Nour" in text
    assert "240" in text
```

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_bot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.bot'`.

- [ ] **Step 3: Create `backend/app/bot.py`**

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.db import connect, init_schema
from app.models import get_quiz_by_slug, leaderboard


def leaderboard_text(conn, slug: str) -> str:
    quiz = get_quiz_by_slug(conn, slug)
    if not quiz:
        return "لا توجد مسابقة بهذا الاسم."
    rows = leaderboard(conn, quiz["id"])
    if not rows:
        return f"لا نتائج بعد في: {quiz['title_ar']}"
    lines = [f"🏆 لوحة الصدارة — {quiz['title_ar']}"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['first_name']} — {r['best_score']}")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = settings.public_url.rstrip("/") + "/app/"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("ابدأ المسابقة 🎮", web_app=WebAppInfo(url=url))]])
    await update.message.reply_text("أهلاً بك في مسابقة الجلسات! اضغط للبدء:", reply_markup=kb)


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        await update.message.reply_text(leaderboard_text(conn, "journals"))
    finally:
        conn.close()


def build_application() -> Application:
    app = Application.builder().token(settings.bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    return app


def main():
    build_application().run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd backend && pytest tests/test_bot.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/bot.py backend/tests/test_bot.py
git commit -m "feat: Telegram bot with Mini App launch and leaderboard"
```

---

### Task 12: Containerization, deploy doc, end-to-end checklist

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `docs/DEPLOY.md`, `.env.example`

**Interfaces:**
- Produces a runnable stack: one container runs Uvicorn (API + Mini App) and one runs the bot (or a single image with two compose services sharing the `content/` and DB volume).

- [ ] **Step 1: Create `.env.example`**

```bash
BOT_TOKEN=123456:replace-with-botfather-token
PUBLIC_URL=https://your-domain.example
QUIZ_DB_PATH=/data/quiz.db
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY backend/pyproject.toml backend/pyproject.toml
RUN pip install --no-cache-dir -e backend/.
COPY backend/ backend/
COPY frontend/ frontend/
COPY content/ content/
WORKDIR /srv/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  web:
    build: .
    env_file: .env
    environment:
      QUIZ_DB_PATH: /data/quiz.db
    volumes:
      - quizdata:/data
      - ./content:/srv/content
    ports:
      - "8000:8000"
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  bot:
    build: .
    env_file: .env
    environment:
      QUIZ_DB_PATH: /data/quiz.db
    volumes:
      - quizdata:/data
      - ./content:/srv/content
    command: ["python", "-m", "app.bot"]
volumes:
  quizdata:
```

- [ ] **Step 4: Create `docs/DEPLOY.md`**

```markdown
# Deploy

## Prerequisites
- A bot token from @BotFather.
- An HTTPS domain pointing at the host (Telegram Mini Apps require HTTPS).

## Steps
1. `cp .env.example .env` and fill `BOT_TOKEN` + `PUBLIC_URL` (the public HTTPS URL).
2. Seed the database once:
   `docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_from_file; c=connect('/data/quiz.db'); init_schema(c); seed_from_file(c,'/srv/content/questions/journals.json')"`
3. `docker compose up -d --build`.
4. Put a TLS-terminating reverse proxy (your existing setup) in front of `web:8000` for `PUBLIC_URL`.
5. In @BotFather: set the Mini App / menu button URL to `PUBLIC_URL/app/`.
6. Open the bot, press **/start**, then the **ابدأ المسابقة** button.

## Notes
- The bot uses long polling (no inbound webhook needed). Only the Mini App needs the public HTTPS URL.
- Scores persist in the `quizdata` volume.
```

- [ ] **Step 5: End-to-end manual checklist (run once, real Telegram)**

- [ ] `docker compose up -d --build` succeeds; `curl -s localhost:8000/health` → `{"status":"ok"}`.
- [ ] Seed step populated the journals quiz (`curl -s localhost:8000/api/quizzes` lists it).
- [ ] In Telegram, `/start` shows the **ابدأ المسابقة** button; tapping opens the RTL Mini App.
- [ ] Playing answers each question; images render from `/content/...`.
- [ ] Finishing shows the report (score, rank, per-question review with source screenshots + page).
- [ ] `/leaderboard` in chat lists your name and score.
- [ ] A second contestant appears on the leaderboard, ranked correctly.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml docs/DEPLOY.md .env.example
git commit -m "feat: containerization, deploy docs, e2e checklist"
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Telegram Mini App + bot → Tasks 1, 8, 10, 11. ✓
- Per-contestant detailed report → Task 7 (build) + 10 (UI) + 11 (DM text). ✓
- Leaderboard → Tasks 6 (query), 8 (API), 10 (UI), 11 (bot). ✓
- Real questions from PDFs + real-world artifacts → Task 9 (extraction + curated content + sourced assets). ✓
- Question types mcq/tf/image → schema (Task 5), runner (Task 10). `match`/`order` correctly deferred to Phase 2 per Global Constraints. ✓
- Server-authoritative scoring + speed/streak → Task 3 + Task 8 wiring. ✓
- Telegram identity via initData HMAC → Task 4 + Task 8. ✓
- SQLite storage → Task 2. ✓
- Self-paced (async) flow → covered end-to-end. Live mode is **Phase 3** (out of scope here), matching the spec's phasing. ✓
- Deployment via Docker host → Task 12. ✓

**Placeholder scan:** No "TBD/TODO/handle edge cases" in code steps. The one intentionally human/interactive step is Task 9 Steps 3–5 (reading real PDF text, sourcing real screenshots, writing curated Arabic questions) — this is inherent to the "real source" requirement and is bounded by the schema validator (Task 5) and a concrete JSON skeleton.

**Type consistency:** Function names and shapes are consistent across tasks — `score_answer`, `validate_init_data`, `validate_quiz`, `seed_quiz`/`seed_from_file`, `build_report`/`format_report_text`, `leaderboard`, `leaderboard_text`, and the question dict shape (`id,type,prompt_ar,options_ar,asset_file,base_points`) match between API (Task 8) and frontend (Task 10).

## Out of scope (future plans)
- **Phase 2:** remaining 3 quizzes, `match`/`order` question types, badges/streak surfacing in UI, overall leaderboard, bot auto-DM of the report after finishing.
- **Phase 3:** live timed sessions (join codes, polled shared board), WebSocket upgrade.
```
