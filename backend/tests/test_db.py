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
