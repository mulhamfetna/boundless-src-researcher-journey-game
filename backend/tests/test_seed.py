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
