from app.badges import evaluate, award, get_badges, top_badge


def test_evaluate_all_conditions():
    s = {"accuracy": 1.0, "max_streak": 6, "hints_used": 0, "is_first_finish": True}
    # perfect + no hints also earns the combined "flawless" badge
    assert set(evaluate(s)) == {"perfect_quiz", "streak_master", "self_reliant", "first_finish", "flawless"}


def test_evaluate_none():
    s = {"accuracy": 0.5, "max_streak": 2, "hints_used": 1, "is_first_finish": False}
    assert evaluate(s) == []


def test_self_reliant_only_with_zero_hints():
    assert "self_reliant" in evaluate({"accuracy": 0, "max_streak": 0, "hints_used": 0, "is_first_finish": False})
    assert "self_reliant" not in evaluate({"accuracy": 0, "max_streak": 0, "hints_used": 3, "is_first_finish": False})


def test_award_idempotent_and_returns_new(conn):
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.commit()
    new1 = award(conn, 1, ["perfect_quiz", "first_finish"], "2026-06-26T10:00:00")
    assert set(new1) == {"perfect_quiz", "first_finish"}
    new2 = award(conn, 1, ["perfect_quiz", "self_reliant"], "2026-06-26T10:01:00")
    assert new2 == ["self_reliant"]
    assert set(get_badges(conn, 1)) == {"perfect_quiz", "first_finish", "self_reliant"}


def test_top_badge_priority(conn):
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (1, datetime('now'))")
    conn.commit()
    award(conn, 1, ["first_finish", "streak_master"], "2026-06-26T10:00:00")
    assert top_badge(conn, 1) == "streak_master"
    award(conn, 1, ["perfect_quiz"], "2026-06-26T10:01:00")
    assert top_badge(conn, 1) == "perfect_quiz"
    assert top_badge(conn, 999) is None


def test_perfect_quiz_requires_full_sample():
    # accuracy 1.0 but fewer answered than the threshold -> no perfect
    assert "perfect_quiz" not in evaluate({"accuracy": 1.0, "answered": 1, "perfect_min": 10})
    # full sample answered, flawless -> perfect
    assert "perfect_quiz" in evaluate({"accuracy": 1.0, "answered": 10, "perfect_min": 10})


def test_expanded_per_attempt_badges():
    from app.badges import evaluate
    s = {"accuracy": 1.0, "max_streak": 10, "hints_used": 0, "answered": 10, "perfect_min": 10, "slug": "capstone"}
    codes = set(evaluate(s))
    assert {"streak_10", "flawless", "perfect_capstone"} <= codes
    s2 = {"accuracy": 1.0, "max_streak": 3, "hints_used": 0, "answered": 6, "perfect_min": 6, "slug": "journals"}
    c2 = set(evaluate(s2))
    assert "flawless" in c2 and "perfect_capstone" not in c2 and "streak_10" not in c2


def test_evaluate_stateful(conn):
    from app.badges import evaluate_stateful
    conn.execute("INSERT INTO contestants (telegram_user_id, created_at) VALUES (7, datetime('now'))")
    slugs = ["foundations", "journals", "paper-types", "paper-parts", "publishing", "submission"]
    for s in slugs:
        conn.execute("INSERT INTO quizzes (slug, title_ar, pdf_filename) VALUES (?, ?, ?)", (s, s, "x.pdf"))
    conn.commit()
    assert evaluate_stateful(conn, 7) == []
    qids = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM quizzes")}
    for s in slugs[:5]:
        conn.execute("INSERT INTO attempts (contestant_id, quiz_id, mode, finished_at) VALUES (7, ?, 'async', datetime('now'))", (qids[s],))
    conn.commit()
    assert "all_stations" not in evaluate_stateful(conn, 7)
    conn.execute("INSERT INTO attempts (contestant_id, quiz_id, mode, finished_at) VALUES (7, ?, 'async', datetime('now'))", (qids[slugs[5]],))
    conn.commit()
    assert "all_stations" in evaluate_stateful(conn, 7)
    # 6 finished so far; add 4 more -> 10 -> dedicated
    for _ in range(4):
        conn.execute("INSERT INTO attempts (contestant_id, quiz_id, mode, finished_at) VALUES (7, ?, 'async', datetime('now'))", (qids['journals'],))
    conn.commit()
    assert "dedicated" in evaluate_stateful(conn, 7)
