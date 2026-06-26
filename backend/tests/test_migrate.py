import sqlite3
from app.db import connect, init_schema
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


def test_migrate_idempotent_on_fresh_install(tmp_path):
    conn = connect(str(tmp_path / "fresh.db"))
    init_schema(conn)            # current schema, nothing to migrate
    assert migrate(conn) == []
