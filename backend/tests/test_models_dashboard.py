from app.models import (
    upsert_contestant, create_attempt, finish_attempt, record_answer,
    get_questions, get_contestant_answers, get_contestant_attempts, quiz_of_concept,
)
from app.seed import seed_quiz


DOC = {
    "slug": "journals", "title_ar": "المجلات", "pdf_filename": "x.pdf",
    "questions": [
        {"type": "tf", "prompt_ar": "س1", "options_ar": ["صح", "خطأ"], "correct_index": 0, "concept": "indexing"},
        {"type": "tf", "prompt_ar": "س2", "options_ar": ["صح", "خطأ"], "correct_index": 0, "concept": "metrics"},
    ],
}


def _setup(conn):
    quiz_id = seed_quiz(conn, DOC)
    qs = get_questions(conn, quiz_id)
    uid = upsert_contestant(conn, {"id": 1, "first_name": "A"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-27T10:00:00")
    record_answer(conn, aid, qs[0]["id"], {}, True, 0, 100, retries=0, hint_used=0)
    record_answer(conn, aid, qs[1]["id"], {}, True, 0, 80, retries=2, hint_used=1)
    finish_attempt(conn, aid, 180, 0.5, 1000, "2026-06-27T10:00:10")
    return uid, quiz_id


def test_get_contestant_answers_has_concept_and_order(conn):
    uid, _ = _setup(conn)
    rows = get_contestant_answers(conn, uid)
    assert len(rows) == 2
    concepts = {r["concept"] for r in rows}
    assert concepts == {"indexing", "metrics"}
    assert all("order" in r and "retries" in r and "hint_used" in r for r in rows)
    # order is strictly increasing in insertion order
    assert rows[0]["order"] < rows[1]["order"]


def test_get_contestant_answers_only_finished(conn):
    uid, quiz_id = _setup(conn)
    # an unfinished attempt's answers must be excluded
    qs = get_questions(conn, quiz_id)
    aid2 = create_attempt(conn, uid, quiz_id, "async", "2026-06-27T11:00:00")
    record_answer(conn, aid2, qs[0]["id"], {}, True, 0, 100, retries=0, hint_used=0)
    rows = get_contestant_answers(conn, uid)
    assert len(rows) == 2  # still only the finished attempt's answers


def test_get_contestant_attempts(conn):
    uid, _ = _setup(conn)
    rows = get_contestant_attempts(conn, uid)
    assert len(rows) == 1
    assert rows[0]["quiz_title_ar"] == "المجلات"
    assert rows[0]["total_score"] == 180
    assert rows[0]["max_streak"] == 0  # not set in this attempt


def test_quiz_of_concept(conn):
    _setup(conn)
    qoc = quiz_of_concept(conn)
    assert qoc["indexing"]["quiz_slug"] == "journals"
    assert qoc["metrics"]["quiz_title_ar"] == "المجلات"
