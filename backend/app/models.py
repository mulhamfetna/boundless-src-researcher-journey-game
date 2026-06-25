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
