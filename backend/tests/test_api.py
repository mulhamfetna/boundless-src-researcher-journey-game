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
    return TestClient(main_module.app)


def test_list_quizzes(api_client):
    resp = api_client.get("/api/quizzes")
    assert resp.status_code == 200
    assert resp.json()[0]["slug"] == "journals"


def test_get_questions_hides_correct_index(api_client):
    resp = api_client.get("/api/quizzes/journals/questions")
    body = resp.json()
    assert len(body["questions"]) == 2
    assert "correct_index" not in body["questions"][0]


def test_submit_scores_and_returns_report(api_client):
    init = _init_data({"id": 99, "first_name": "Omar"})
    questions = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    answers = [
        {"question_id": questions[0]["id"], "index": 2, "time_ms": 1000},
        {"question_id": questions[1]["id"], "index": 0, "time_ms": 1500},
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
        json={"answers": [{"question_id": questions[0]["id"], "index": 2, "time_ms": 500}], "duration_ms": 500},
    )
    board = api_client.get("/api/leaderboard?slug=journals").json()
    assert board[0]["first_name"] == "Omar"
    assert board[0]["best_score"] > 0
