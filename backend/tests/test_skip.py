"""Skipping a question (issue #29).

A learner must be able to move past a question they cannot solve, but skipping
has to cost something or it becomes the cheapest way to finish. The rule:
zero points, counts as not-first-try (breaks the streak, lowers accuracy), and
the answer is recorded as incorrect so the report tells the truth.

Scored SERVER-side: the client only reports that it skipped.
"""
import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.config import settings
from app.db import connect, init_schema

BOT_TOKEN = "test-token"


def _init_data(user):
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    db_file = str(tmp_path / "skip.db")
    conn = connect(db_file)
    init_schema(conn)
    from app.seed import seed_all
    seed_all(conn, "../content/questions")
    monkeypatch.setattr(settings, "bot_token", BOT_TOKEN)
    monkeypatch.setattr(settings, "db_path", db_file)
    from app import main
    with TestClient(main.app) as c:
        yield c


def _submit(client, answers):
    return client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": _init_data({"id": 501, "first_name": "Ekko"})},
        json={"answers": answers, "duration_ms": 1000},
    )


def test_a_skipped_question_scores_zero(api_client):
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    solved = _submit(api_client, [{"question_id": qs[0]["id"], "retries": 0, "hint_used": False}])
    skipped = _submit(api_client, [{"question_id": qs[0]["id"], "retries": 0, "hint_used": False,
                                    "skipped": True}])
    assert solved.status_code == 200 and skipped.status_code == 200
    assert solved.json()["total_score"] > 0
    assert skipped.json()["total_score"] == 0


def test_skipping_is_worse_than_retrying_many_times(api_client):
    """Retrying floors at 10% of base — skipping must be strictly cheaper."""
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    struggled = _submit(api_client, [{"question_id": qs[0]["id"], "retries": 9, "hint_used": True}])
    skipped = _submit(api_client, [{"question_id": qs[0]["id"], "retries": 0, "hint_used": False,
                                    "skipped": True}])
    assert struggled.json()["total_score"] > skipped.json()["total_score"] == 0


def test_a_skip_breaks_the_streak_and_lowers_accuracy(api_client):
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    answers = [
        {"question_id": qs[0]["id"], "retries": 0, "hint_used": False},
        {"question_id": qs[1]["id"], "retries": 0, "hint_used": False, "skipped": True},
        {"question_id": qs[2]["id"], "retries": 0, "hint_used": False},
    ]
    body = _submit(api_client, answers).json()
    assert body["accuracy"] == pytest.approx(2 / 3)
    assert body["max_streak"] == 1, "the skip must break the streak, not carry it through"


def test_the_report_records_a_skip_as_not_correct(api_client):
    qs = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    body = _submit(api_client, [
        {"question_id": qs[0]["id"], "retries": 0, "hint_used": False, "skipped": True},
    ]).json()
    item = body["items"][0]
    assert item["is_correct"] is False
    assert item.get("skipped") is True
