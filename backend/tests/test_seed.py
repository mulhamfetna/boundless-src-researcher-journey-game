import json as _json
from app.models import get_quiz_by_slug, get_questions, get_asset_for_question
from app.seed import seed_quiz
from tests.conftest import SAMPLE_DOC


def test_seed_inserts_quiz_and_questions(seeded):
    conn, quiz_id = seeded
    quiz = get_quiz_by_slug(conn, "journals")
    assert quiz["id"] == quiz_id
    questions = get_questions(conn, quiz_id)
    assert len(questions) == 2
    assert questions[0]["prompt_ar"] == "سؤال 1"


def test_seed_attaches_asset_to_image_question(seeded):
    conn, quiz_id = seeded
    image_q = get_questions(conn, quiz_id)[1]
    asset = get_asset_for_question(conn, image_q["id"])
    assert asset is not None
    assert asset["file_path"] == "assets/journals/compare.png"


def test_seed_is_idempotent(conn):
    seed_quiz(conn, SAMPLE_DOC)
    seed_quiz(conn, SAMPLE_DOC)
    assert len(get_questions(conn, get_quiz_by_slug(conn, "journals")["id"])) == 2


def test_seed_stores_match_and_order_payloads(conn):
    doc = {
        "slug": "mix", "title_ar": "t", "pdf_filename": "f.pdf",
        "questions": [
            {"type": "match", "prompt_ar": "طابق", "left_ar": ["L0", "L1"],
             "right_ar": ["R0", "R1"], "correct_pairs": [[0, 1], [1, 0]]},
            {"type": "order", "prompt_ar": "رتّب", "items_ar": ["A", "B"],
             "correct_sequence": [1, 0]},
        ],
    }
    seed_quiz(conn, doc)
    qs = get_questions(conn, get_quiz_by_slug(conn, "mix")["id"])
    m = _json.loads(qs[0]["data_json"])
    assert m["correct_pairs"] == [[0, 1], [1, 0]] and m["left_ar"] == ["L0", "L1"]
    o = _json.loads(qs[1]["data_json"])
    assert o["correct_sequence"] == [1, 0] and o["items_ar"] == ["A", "B"]
