import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.db import connect, init_schema
from app.main import app
from app.seed import seed_quiz
from tests.conftest import SAMPLE_DOC

client = TestClient(app)

BOT_TOKEN = "123456:TESTTOKEN"


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def _init_data(user):
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "api.db")
    conn = connect(db_file)
    init_schema(conn)
    seed_quiz(conn, SAMPLE_DOC)
    monkeypatch.setattr(main_module, "_conn", conn, raising=False)
    main_module.app.state.conn = conn
    monkeypatch.setattr(main_module.settings, "bot_token", BOT_TOKEN, raising=False)
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    return TestClient(main_module.app)


def test_list_quizzes(api_client):
    resp = api_client.get("/api/quizzes")
    assert resp.status_code == 200
    assert resp.json()[0]["slug"] == "journals"


def test_get_questions_exposes_answer_key(api_client):
    body = api_client.get("/api/quizzes/journals/questions").json()
    assert "correct_index" in body["questions"][0]
    assert "fun_facts_ar" in body
    q0 = body["questions"][0]
    assert "hint_ar" in q0
    assert "option_explanations_ar" in q0  # first question is an option type


def test_submit_scores_and_returns_report(api_client):
    init = _init_data({"id": 99, "first_name": "Omar"})
    questions = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    answers = [
        {"question_id": questions[0]["id"], "retries": 0, "hint_used": False},
        {"question_id": questions[1]["id"], "retries": 0, "hint_used": False},
    ]
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": answers, "duration_ms": 2500},
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["total_score"] > 0
    assert len(report["items"]) == 2
    assert all(it["is_correct"] for it in report["items"])


def test_submit_rejects_bad_initdata(api_client):
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": "auth_date=1&hash=deadbeef"},
        json={"answers": [], "duration_ms": 0},
    )
    assert resp.status_code == 401


def test_leaderboard_after_submit(api_client):
    init = _init_data({"id": 99, "first_name": "Omar"})
    questions = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": [{"question_id": questions[0]["id"], "retries": 0, "hint_used": False}], "duration_ms": 500},
    )
    board = api_client.get("/api/leaderboard?slug=journals").json()
    assert board[0]["first_name"] == "Omar"
    assert board[0]["best_score"] > 0


def _seed_order_question(client_db_conn):
    import json as _j
    client_db_conn.execute(
        "INSERT INTO questions (quiz_id,type,prompt_ar,base_points,explanation_ar,source_page,data_json,display_order) "
        "VALUES ((SELECT id FROM quizzes WHERE slug='journals'),'order','رتّب',100,'',1,?,9)",
        (_j.dumps({"items_ar": ["A", "B", "C"], "correct_sequence": [2, 0, 1]}),),
    )
    client_db_conn.commit()


def test_questions_exposes_order_items_no_answer(api_client):
    main_module = __import__("app.main", fromlist=["app"])
    _seed_order_question(main_module._conn)
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    oq = [q for q in qs if q["type"] == "order"][0]
    assert oq["items_ar"] == ["A", "B", "C"]
    assert "correct_sequence" in oq


def test_submit_order_partial_and_first_finish_badge(api_client, monkeypatch):
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    main_module = __import__("app.main", fromlist=["app"])
    _seed_order_question(main_module._conn)
    init = _init_data({"id": 555, "first_name": "Lina"})
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    oq = [q for q in qs if q["type"] == "order"][0]
    # correct order -> full credit
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": [{"question_id": oq["id"], "retries": 0, "hint_used": False}], "duration_ms": 800},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["items"][0]["is_correct"] is True
    assert "first_finish" in body["earned_now"]


def test_partial_submission_does_not_earn_perfect(api_client, monkeypatch):
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    main_module = __import__("app.main", fromlist=["app"])
    _seed_order_question(main_module._conn)
    init = _init_data({"id": 4242, "first_name": "Test"})
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    oq = [q for q in qs if q["type"] == "order"][0]
    resp = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": [{"question_id": oq["id"], "retries": 0, "hint_used": False}], "duration_ms": 500},
    )
    body = resp.json()
    # Even though answering 1 question first-try makes per-answered accuracy 1.0,
    # perfect_quiz is gated on answering a full sample, so it isn't earned here.
    assert "perfect_quiz" not in body["earned_now"]


def test_me_badges_requires_initdata(api_client):
    assert api_client.get("/api/me/badges", headers={"X-Init-Data": "bad&hash=x"}).status_code == 401


def test_overall_leaderboard(api_client, monkeypatch):
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    init = _init_data({"id": 7, "first_name": "Omar"})
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    mcq = [q for q in qs if q["type"] in ("mcq", "tf", "image")][0]
    api_client.post("/api/quizzes/journals/submit", headers={"X-Init-Data": init},
                    json={"answers": [{"question_id": mcq["id"], "retries": 0, "hint_used": False}], "duration_ms": 500})
    board = api_client.get("/api/leaderboard?scope=overall").json()
    assert board and "total_score" in board[0] and "top_badge" in board[0]


def test_get_questions_samples_to_sample_size(tmp_path):
    conn = connect(str(tmp_path / "s.db"))
    init_schema(conn)
    questions = [
        {"type": "tf", "prompt_ar": f"س{i}", "options_ar": ["صح", "خطأ"],
         "correct_index": i % 2, "concept": ["a", "b", "c"][i % 3]}
        for i in range(15)
    ]
    seed_quiz(conn, {"slug": "big", "title_ar": "ك", "pdf_filename": "x.pdf",
                     "questions": questions})
    main_module.app.state.conn = conn
    c = TestClient(main_module.app)

    body = c.get("/api/quizzes/big/questions").json()
    assert len(body["questions"]) == 10
    assert all("concept" in q for q in body["questions"])
    ids = {q["id"] for q in body["questions"]}
    assert len(ids) == 10  # no duplicates


def test_submit_accuracy_ignores_unanswered_bank_questions(tmp_path, monkeypatch):
    conn = connect(str(tmp_path / "acc.db"))
    init_schema(conn)
    seed_quiz(conn, {"slug": "acc", "title_ar": "د", "pdf_filename": "x.pdf",
        "questions": [
            {"type": "tf", "prompt_ar": f"س{i}", "options_ar": ["صح", "خطأ"],
             "correct_index": 0, "concept": "a"} for i in range(3)
        ]})
    main_module.app.state.conn = conn
    monkeypatch.setattr(main_module.settings, "bot_token", BOT_TOKEN, raising=False)
    import app.notify as notify
    monkeypatch.setattr(notify, "send_report_dm", lambda *a, **k: True)
    c = TestClient(main_module.app)

    init = _init_data({"id": 9, "first_name": "Z"})
    qs = c.get("/api/quizzes/acc/questions").json()["questions"]
    answers = [{"question_id": qs[0]["id"], "retries": 0, "hint_used": False},
               {"question_id": qs[1]["id"], "retries": 0, "hint_used": False}]
    report = c.post("/api/quizzes/acc/submit",
                    headers={"X-Init-Data": init},
                    json={"answers": answers, "duration_ms": 500}).json()
    assert report["accuracy"] == 1.0  # 2 first-try / 2 answered, NOT 2/3
