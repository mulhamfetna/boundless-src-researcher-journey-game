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
