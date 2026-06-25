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
