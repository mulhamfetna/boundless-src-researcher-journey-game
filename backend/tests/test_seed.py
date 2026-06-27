import json as _json
import json as _json2
from app.models import (
    get_quiz_by_slug, get_questions, get_asset_for_question,
    upsert_contestant, create_attempt, record_answer,
)
from app.models import get_quiz_by_slug as _gqs
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


def test_seed_replaces_quiz_with_live_play_data(conn):
    """Re-seeding a quiz that has real attempts/answers must not raise FK errors."""
    # Initial seed.
    quiz_id = seed_quiz(conn, SAMPLE_DOC)
    questions = get_questions(conn, quiz_id)

    # Simulate live play data: one contestant, one attempt, one answer.
    uid = upsert_contestant(conn, {"id": 42, "first_name": "Test"})
    attempt_id = create_attempt(conn, uid, quiz_id, "async", "2026-01-01T00:00:00")
    record_answer(conn, attempt_id, questions[0]["id"], 2, True, 1000, 100)

    # Re-seed (content reset) — must NOT raise FOREIGN KEY constraint failed.
    new_quiz_id = seed_quiz(conn, SAMPLE_DOC)

    # Quiz is still intact with expected questions.
    new_questions = get_questions(conn, new_quiz_id)
    assert len(new_questions) == 2
    assert new_questions[0]["prompt_ar"] == "سؤال 1"


def test_seed_stores_match_and_order_payloads(conn):
    doc = {
        "slug": "mix", "title_ar": "t", "pdf_filename": "f.pdf",
        "questions": [
            {"type": "match", "prompt_ar": "طابق", "left_ar": ["L0", "L1"],
             "right_ar": ["R0", "R1"], "correct_pairs": [[0, 1], [1, 0]], "concept": "indexing"},
            {"type": "order", "prompt_ar": "رتّب", "items_ar": ["A", "B"],
             "correct_sequence": [1, 0], "concept": "indexing"},
        ],
    }
    seed_quiz(conn, doc)
    qs = get_questions(conn, get_quiz_by_slug(conn, "mix")["id"])
    m = _json.loads(qs[0]["data_json"])
    assert m["correct_pairs"] == [[0, 1], [1, 0]] and m["left_ar"] == ["L0", "L1"]
    o = _json.loads(qs[1]["data_json"])
    assert o["correct_sequence"] == [1, 0] and o["items_ar"] == ["A", "B"]


def test_seed_stores_explainers_hint_funfacts(conn):
    doc = {
        "slug": "kx", "title_ar": "t", "pdf_filename": "f.pdf",
        "fun_facts_ar": ["حقيقة 1", "حقيقة 2"],
        "questions": [{
            "type": "mcq", "prompt_ar": "س", "options_ar": ["أ", "ب", "ج", "د"],
            "correct_index": 2, "option_explanations_ar": ["لا", "لا", "نعم", "لا"], "hint_ar": "فكّر",
            "concept": "indexing",
        }],
    }
    seed_quiz(conn, doc)
    quiz = _gqs(conn, "kx")
    assert _json2.loads(quiz["fun_facts_json"]) == ["حقيقة 1", "حقيقة 2"]
    q = get_questions(conn, quiz["id"])[0]
    data = _json2.loads(q["data_json"])
    assert data["option_explanations_ar"][2] == "نعم"
    assert data["hint_ar"] == "فكّر"


def test_seed_persists_concept_in_data_json(conn):
    doc = {
        "slug": "concepttest", "title_ar": "ت", "pdf_filename": "x.pdf",
        "questions": [
            {"type": "tf", "prompt_ar": "س", "options_ar": ["صح", "خطأ"],
             "correct_index": 0, "concept": "indexing"},
        ],
    }
    seed_quiz(conn, doc)
    q = get_questions(conn, get_quiz_by_slug(conn, "concepttest")["id"])[0]
    assert _json.loads(q["data_json"])["concept"] == "indexing"


def test_seed_persists_passage_and_source(conn):
    doc = {
        "slug": "ap", "title_ar": "ت", "pdf_filename": "x.pdf",
        "questions": [{"type": "mcq", "prompt_ar": "س", "options_ar": ["أ", "ب"],
                       "correct_index": 0, "concept": "abstract",
                       "passage": "We study X.", "source_url": "https://doaj.org/a/1"}],
    }
    seed_quiz(conn, doc)
    q = get_questions(conn, get_quiz_by_slug(conn, "ap")["id"])[0]
    data = _json.loads(q["data_json"])
    assert data["passage"] == "We study X."
    assert data["source_url"] == "https://doaj.org/a/1"
