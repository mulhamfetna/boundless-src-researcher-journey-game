import json
from app.models import upsert_contestant, create_attempt, finish_attempt, record_answer, get_questions, get_quiz_by_slug
from app.report import build_report, format_report_text
from app.badges import award


def _seed_attempt(conn, quiz_id):
    uid = upsert_contestant(conn, {"id": 7, "first_name": "Sara"})
    attempt_id = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    questions = get_questions(conn, quiz_id)
    record_answer(conn, attempt_id, questions[0]["id"], {"index": 2}, True, 1000, 150)
    record_answer(conn, attempt_id, questions[1]["id"], {"index": 1}, False, 2000, 0)
    finish_attempt(conn, attempt_id, 150, 0.5, 3000, "2026-06-25T10:00:05")
    return attempt_id


def test_build_report_shape(seeded):
    conn, quiz_id = seeded
    attempt_id = _seed_attempt(conn, quiz_id)
    report = build_report(conn, attempt_id)
    assert report["total_score"] == 150
    assert report["accuracy"] == 0.5
    assert len(report["items"]) == 2
    first = report["items"][0]
    assert first["is_correct"] is True
    assert first["type"] == "mcq"
    assert first["first_try"] is True
    assert "retries" in first


def test_build_report_includes_asset_for_image(seeded):
    conn, quiz_id = seeded
    attempt_id = _seed_attempt(conn, quiz_id)
    report = build_report(conn, attempt_id)
    assert report["items"][1]["asset_file"] == "assets/journals/compare.png"


def test_format_report_text_is_arabic_summary(seeded):
    conn, quiz_id = seeded
    attempt_id = _seed_attempt(conn, quiz_id)
    report = build_report(conn, attempt_id)
    text = format_report_text(report, "تصنيف المجلات")
    assert "150" in text
    assert "تصنيف المجلات" in text


def test_report_includes_max_streak_and_badges(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 3, "first_name": "Z"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    qs = get_questions(conn, quiz_id)
    record_answer(conn, aid, qs[0]["id"], {"index": 2}, True, 1000, 150)
    finish_attempt(conn, aid, 150, 1.0, 1500, "2026-06-25T10:00:05")
    conn.execute("UPDATE attempts SET max_streak=2 WHERE id=?", (aid,))
    conn.commit()
    award(conn, uid, ["perfect_quiz"], "2026-06-25T10:00:05")
    report = build_report(conn, aid)
    assert report["max_streak"] == 2
    assert "perfect_quiz" in report["all_badges"]


def test_report_handles_order_answer(seeded):
    conn, quiz_id = seeded
    # add an order question directly
    import json as _j
    conn.execute(
        "INSERT INTO questions (quiz_id,type,prompt_ar,base_points,explanation_ar,source_page,data_json,display_order) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (quiz_id, "order", "رتّب", 100, "", 1,
         _j.dumps({"items_ar": ["A", "B"], "correct_sequence": [1, 0]}), 5),
    )
    conn.commit()
    qid = conn.execute("SELECT id FROM questions WHERE type='order'").fetchone()["id"]
    uid = upsert_contestant(conn, {"id": 4, "first_name": "Q"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-25T10:00:00")
    record_answer(conn, aid, qid, {"sequence": [1, 0]}, True, 1000, 100)
    finish_attempt(conn, aid, 100, 1.0, 1000, "2026-06-25T10:00:05")
    report = build_report(conn, aid)
    item = report["items"][0]
    assert item["type"] == "order"
    assert item["is_correct"] is True
