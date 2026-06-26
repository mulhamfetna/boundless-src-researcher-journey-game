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
