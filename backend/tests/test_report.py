import json
from app.models import upsert_contestant, create_attempt, finish_attempt, record_answer, get_questions, get_quiz_by_slug
from app.report import build_report, format_report_text


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
    assert first["correct_index"] == 2
    assert first["given_index"] == 2


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
