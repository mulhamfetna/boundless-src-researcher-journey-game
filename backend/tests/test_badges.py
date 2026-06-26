from app.badges import evaluate, award, get_badges, top_badge


def test_evaluate_all_conditions():
    s = {"accuracy": 1.0, "max_streak": 6, "avg_speed_bonus": 40.0, "is_first_finish": True}
    codes = set(evaluate(s))
    assert codes == {"perfect_quiz", "streak_master", "speed_demon", "first_finish"}


def test_evaluate_none():
    s = {"accuracy": 0.5, "max_streak": 2, "avg_speed_bonus": 10.0, "is_first_finish": False}
    assert evaluate(s) == []


def test_evaluate_thresholds():
    assert "speed_demon" in evaluate({"accuracy": 0, "max_streak": 0, "avg_speed_bonus": 35.0, "is_first_finish": False})
    assert "speed_demon" not in evaluate({"accuracy": 0, "max_streak": 0, "avg_speed_bonus": 34.9, "is_first_finish": False})
    assert "streak_master" in evaluate({"accuracy": 0, "max_streak": 5, "avg_speed_bonus": 0, "is_first_finish": False})


def test_award_idempotent_and_returns_new(conn):
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.commit()
    new1 = award(conn, 1, ["perfect_quiz", "first_finish"], "2026-06-26T10:00:00")
    assert set(new1) == {"perfect_quiz", "first_finish"}
    new2 = award(conn, 1, ["perfect_quiz", "speed_demon"], "2026-06-26T10:01:00")
    assert new2 == ["speed_demon"]
    assert set(get_badges(conn, 1)) == {"perfect_quiz", "first_finish", "speed_demon"}


def test_top_badge_priority(conn):
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.commit()
    award(conn, 1, ["first_finish", "streak_master"], "2026-06-26T10:00:00")
    assert top_badge(conn, 1) == "streak_master"
    award(conn, 1, ["perfect_quiz"], "2026-06-26T10:01:00")
    assert top_badge(conn, 1) == "perfect_quiz"
    assert top_badge(conn, 999) is None
