from app.models import insert_issue_report, list_issue_reports


def test_insert_and_list_issue_reports(conn):
    insert_issue_report(conn, {
        "telegram_user_id": 5, "username": "lina", "first_name": "Lina",
        "language_code": "ar", "is_premium": 1, "text": "زر لا يعمل",
        "platform": "ios", "raw_json": "{}",
    })
    insert_issue_report(conn, {"telegram_user_id": 6, "text": "ملاحظة"})
    rows = list_issue_reports(conn, limit=10)
    assert len(rows) == 2
    assert rows[0]["telegram_user_id"] == 6
    assert rows[1]["username"] == "lina"
    assert rows[1]["text"] == "زر لا يعمل"


from app.bot import is_admin, format_reports


def test_is_admin():
    assert is_admin(7, 7) is True
    assert is_admin(7, 8) is False
    assert is_admin(7, 0) is False


def test_format_reports(conn):
    insert_issue_report(conn, {"telegram_user_id": 5, "username": "lina", "first_name": "Lina",
                               "language_code": "ar", "platform": "ios", "text": "زر معطّل"})
    txt = format_reports(list_issue_reports(conn))
    assert "زر معطّل" in txt
    assert "lina" in txt


def test_format_reports_empty():
    assert "لا" in format_reports([])


import json as _json, hashlib as _hl, hmac as _hm
from urllib.parse import urlencode as _ue
import pytest
from app import main as main_module
from app.db import connect as _connect, init_schema as _init_schema
from app.seed import seed_quiz as _seed_quiz
from tests.conftest import SAMPLE_DOC

_BOT = "123456:TESTTOKEN"


def _init(user):
    fields = {"auth_date": "1700000000", "user": _json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = _hm.new(b"WebAppData", _BOT.encode(), _hl.sha256).digest()
    h = _hm.new(secret, dcs.encode(), _hl.sha256).hexdigest()
    return _ue({**fields, "hash": h})


@pytest.fixture
def rep_client(tmp_path, monkeypatch):
    c = _connect(str(tmp_path / "r.db"))
    _init_schema(c)
    _seed_quiz(c, SAMPLE_DOC)
    main_module.app.state.conn = c
    monkeypatch.setattr(main_module.settings, "bot_token", _BOT, raising=False)
    from fastapi.testclient import TestClient
    return TestClient(main_module.app), c


def test_report_stores_metadata(rep_client):
    client, c = rep_client
    init = _init({"id": 42, "first_name": "Lina", "username": "lina", "language_code": "ar", "is_premium": True})
    resp = client.post("/api/report", headers={"X-Init-Data": init},
                       json={"text": "زر لا يعمل", "platform": "ios", "version": "7.2"})
    assert resp.status_code == 200 and resp.json() == {"ok": True}
    row = c.execute("SELECT * FROM issue_reports ORDER BY id DESC LIMIT 1").fetchone()
    assert row["telegram_user_id"] == 42 and row["username"] == "lina"
    assert row["text"] == "زر لا يعمل" and row["platform"] == "ios"
    assert row["language_code"] == "ar" and row["is_premium"] == 1
    assert row["raw_json"] and "42" in row["raw_json"]


def test_report_empty_text_400(rep_client):
    client, _ = rep_client
    init = _init({"id": 42, "first_name": "L"})
    assert client.post("/api/report", headers={"X-Init-Data": init}, json={"text": "  "}).status_code == 400


def test_report_requires_initdata(rep_client):
    client, _ = rep_client
    assert client.post("/api/report", headers={"X-Init-Data": "bad&hash=x"}, json={"text": "hi"}).status_code == 401
