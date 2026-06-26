from app.bot import overall_leaderboard_text
from app.models import upsert_contestant, create_attempt, finish_attempt


def test_overall_text_lists_summed_scores(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 9, "first_name": "Hala"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-26T10:00:00")
    finish_attempt(conn, aid, 300, 1.0, 5000, "2026-06-26T10:00:05")
    text = overall_leaderboard_text(conn)
    assert "Hala" in text
    assert "300" in text


def test_overall_text_empty_state(seeded):
    conn, quiz_id = seeded
    text = overall_leaderboard_text(conn)
    assert isinstance(text, str) and text  # non-empty message, no crash
