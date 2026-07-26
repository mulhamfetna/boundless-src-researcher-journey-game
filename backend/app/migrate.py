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


def _badges_has_unique(conn):
    for idx in conn.execute("PRAGMA index_list(badges)").fetchall():
        if not idx["unique"]:
            continue
        cols = {r["name"] for r in conn.execute(f"PRAGMA index_info({idx['name']})")}
        if {"contestant_id", "code"} <= cols:
            return True
    return False


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

    # Ensure badges table exists (Phase 1 DBs never had it).
    badges_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='badges'"
    ).fetchone()
    if not badges_exists:
        conn.execute(
            """CREATE TABLE badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contestant_id INTEGER NOT NULL REFERENCES contestants(telegram_user_id),
                code TEXT NOT NULL,
                earned_at TEXT NOT NULL,
                UNIQUE(contestant_id, code)
            )"""
        )
        changes.append("badges.create")

    # Ensure UNIQUE(contestant_id, code) on badges.
    if not _badges_has_unique(conn):
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

    if "retries" not in _columns(conn, "answers"):
        conn.execute("ALTER TABLE answers ADD COLUMN retries INTEGER NOT NULL DEFAULT 0")
        changes.append("answers.retries")
    if "hint_used" not in _columns(conn, "answers"):
        conn.execute("ALTER TABLE answers ADD COLUMN hint_used INTEGER NOT NULL DEFAULT 0")
        changes.append("answers.hint_used")
    if "fun_facts_json" not in _columns(conn, "quizzes"):
        conn.execute("ALTER TABLE quizzes ADD COLUMN fun_facts_json TEXT NOT NULL DEFAULT '[]'")
        changes.append("quizzes.fun_facts_json")

    reports_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='issue_reports'"
    ).fetchone()
    if not reports_exists:
        conn.executescript(
            """
            CREATE TABLE issue_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER, username TEXT, first_name TEXT, last_name TEXT,
                language_code TEXT, is_premium INTEGER, allows_write_to_pm INTEGER,
                auth_date TEXT, chat_type TEXT, chat_instance TEXT, query_id TEXT,
                start_param TEXT, platform TEXT, app_version TEXT,
                text TEXT NOT NULL, raw_json TEXT, created_at TEXT NOT NULL
            );
            """
        )
        changes.append("issue_reports.create")

    duels_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='duels'"
    ).fetchone()
    if not duels_exists:
        conn.executescript(
            """
            CREATE TABLE duels (
                token TEXT PRIMARY KEY,
                question_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                creator_correct INTEGER NOT NULL,
                creator_time_ms INTEGER NOT NULL,
                opponent_id INTEGER,
                opponent_correct INTEGER,
                opponent_time_ms INTEGER,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            );
            """
        )
        changes.append("duels.create")

    conn.commit()
    return changes


def main():
    conn = connect(settings.db_path)
    changes = migrate(conn)
    print("migrated:", changes or "already current")


if __name__ == "__main__":
    main()
