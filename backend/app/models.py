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


def record_answer(conn, attempt_id, question_id, given, is_correct, time_ms, points, retries=0, hint_used=0):
    conn.execute(
        """INSERT INTO answers
           (attempt_id, question_id, given_json, is_correct, time_ms, points_awarded, retries, hint_used)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (attempt_id, question_id, json.dumps(given), int(is_correct), time_ms, points, int(retries), int(hint_used)),
    )
    conn.commit()


def leaderboard(conn, quiz_id, limit=20):
    return conn.execute(
        """
        SELECT c.telegram_user_id AS telegram_user_id, c.first_name AS first_name, MAX(a.total_score) AS best_score
        FROM attempts a
        JOIN contestants c ON c.telegram_user_id = a.contestant_id
        WHERE a.quiz_id = ? AND a.finished_at IS NOT NULL
        GROUP BY a.contestant_id
        ORDER BY best_score DESC
        LIMIT ?
        """,
        (quiz_id, limit),
    ).fetchall()


def set_attempt_max_streak(conn, attempt_id, max_streak):
    conn.execute("UPDATE attempts SET max_streak=? WHERE id=?", (max_streak, attempt_id))
    conn.commit()


def leaderboard_overall(conn, limit=20):
    return conn.execute(
        """
        SELECT best.contestant_id AS telegram_user_id, c.first_name AS first_name, SUM(best.best_score) AS total_score
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
