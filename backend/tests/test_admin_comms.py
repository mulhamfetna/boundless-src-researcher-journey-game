"""Two-way admin communication (issues #34, #35).

#34 A learner's report must REACH the admin, not just land in a table.
#35 The admin must be able to reach learners — everyone, or one person.

The sending function is injected throughout, so the rules (throttling, blocked
users, admin-only) are tested without touching the network.
"""
import pytest

from app.broadcast import Outcome, broadcast, resolve_recipient
from app.db import connect, init_schema
from app import models


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_schema(c)
    now = "2026-01-01T00:00:00Z"
    for uid, uname, first in [(1, "vi", "Vi"), (2, "ekko", "Ekko"), (3, None, "Jinx")]:
        c.execute(
            "INSERT INTO contestants (telegram_user_id, username, first_name, created_at) VALUES (?,?,?,?)",
            (uid, uname, first, now),
        )
    c.commit()
    return c


# ---------------------------------------------------------------- recipients

def test_every_known_user_can_be_reached(conn):
    assert sorted(models.all_contestant_ids(conn)) == [1, 2, 3]


def test_a_user_can_be_found_by_username_with_or_without_the_at(conn):
    assert resolve_recipient(conn, "@ekko") == 2
    assert resolve_recipient(conn, "ekko") == 2


def test_a_user_can_be_found_by_numeric_id(conn):
    assert resolve_recipient(conn, "3") == 3


def test_an_unknown_recipient_resolves_to_nothing(conn):
    assert resolve_recipient(conn, "@nobody") is None


def test_username_lookup_ignores_case(conn):
    assert resolve_recipient(conn, "@EKKO") == 2


# ---------------------------------------------------------------- broadcast

def test_a_broadcast_reaches_everyone_and_reports_the_count():
    sent = []
    result = broadcast([1, 2, 3], "مرحبًا", send=lambda uid, text: sent.append((uid, text)) or True)
    assert [u for u, _ in sent] == [1, 2, 3]
    assert result == Outcome(sent=3, blocked=0, failed=0)


def test_a_user_who_blocked_the_bot_is_counted_not_fatal():
    def send(uid, text):
        if uid == 2:
            raise PermissionError("bot was blocked by the user")
        return True

    result = broadcast([1, 2, 3], "مرحبًا", send=send)
    assert result == Outcome(sent=2, blocked=1, failed=0)
    assert result.total == 3


def test_other_failures_are_counted_separately_and_do_not_stop_the_run():
    def send(uid, text):
        if uid == 2:
            raise RuntimeError("timeout")
        return True

    result = broadcast([1, 2, 3], "مرحبًا", send=send)
    assert result == Outcome(sent=2, blocked=0, failed=1)


def test_sending_is_throttled_so_telegram_does_not_rate_limit_us():
    waits = []
    broadcast([1, 2, 3], "hi", send=lambda u, t: True, sleep=waits.append)
    # A pause between each message, not after the last one.
    assert len(waits) == 2
    assert all(w > 0 for w in waits)


def test_an_empty_audience_is_not_an_error():
    assert broadcast([], "hi", send=lambda u, t: True) == Outcome(sent=0, blocked=0, failed=0)


# ------------------------------------------------- #34 report reaches the admin

def test_a_submitted_report_is_pushed_to_the_admin(monkeypatch, tmp_path):
    """The bug: reports were stored and nobody was told."""
    import hashlib, hmac, json
    from urllib.parse import urlencode
    from fastapi.testclient import TestClient
    from app.config import settings
    from app.seed import seed_all

    token = "test-token"
    db_file = str(tmp_path / "rep.db")
    c = connect(db_file); init_schema(c); seed_all(c, "../content/questions")
    monkeypatch.setattr(settings, "bot_token", token)
    monkeypatch.setattr(settings, "db_path", db_file)
    monkeypatch.setattr(settings, "admin_id", 4242)
    from app import main as main_module
    monkeypatch.setattr(main_module, "_conn", c, raising=False)
    main_module.app.state.conn = c

    delivered = []
    from app import api as api_mod
    monkeypatch.setattr(api_mod.notify, "send_report_dm",
                        lambda uid, text, **kw: delivered.append((uid, text)) or True)

    user = {"id": 77, "first_name": "Lina", "username": "lina"}
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    init = urlencode({**fields, "hash": h})

    from app import main
    with TestClient(main.app) as client:
        resp = client.post("/api/report", headers={"X-Init-Data": init},
                           json={"text": "السؤال الثالث إجابته خاطئة", "platform": "android"})

    assert resp.status_code == 200
    assert delivered, "the admin was never notified"
    admin_id, text = delivered[0]
    assert admin_id == 4242
    assert "السؤال الثالث إجابته خاطئة" in text
    assert "Lina" in text and "lina" in text


def test_a_failing_admin_dm_never_breaks_the_learners_request(monkeypatch, tmp_path):
    import hashlib, hmac, json
    from urllib.parse import urlencode
    from fastapi.testclient import TestClient
    from app.config import settings
    from app.seed import seed_all

    token = "test-token"
    db_file = str(tmp_path / "rep2.db")
    c = connect(db_file); init_schema(c); seed_all(c, "../content/questions")
    monkeypatch.setattr(settings, "bot_token", token)
    monkeypatch.setattr(settings, "db_path", db_file)
    monkeypatch.setattr(settings, "admin_id", 4242)
    from app import main as main_module
    monkeypatch.setattr(main_module, "_conn", c, raising=False)
    main_module.app.state.conn = c

    from app import api as api_mod
    def boom(*a, **k): raise RuntimeError("telegram down")
    monkeypatch.setattr(api_mod.notify, "send_report_dm", boom)

    user = {"id": 78, "first_name": "Vi"}
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    init = urlencode({**fields, "hash": h})

    from app import main
    with TestClient(main.app) as client:
        resp = client.post("/api/report", headers={"X-Init-Data": init}, json={"text": "مشكلة"})
    assert resp.status_code == 200      # the learner still succeeds
    rows = c.execute("SELECT COUNT(*) n FROM issue_reports").fetchone()
    assert rows["n"] == 1               # and the report is still stored


def test_pressing_start_registers_the_user_so_announcements_reach_them(conn):
    """Without this, /announce only reaches people who FINISHED a quiz.

    Contestants were previously created only on attempt submission, so anyone
    who opened the bot and never played was invisible to a broadcast — not
    really "all bot users".
    """
    before = models.all_contestant_ids(conn)
    models.upsert_contestant(conn, {"id": 900, "first_name": "Caitlyn", "username": "cait"})
    after = models.all_contestant_ids(conn)
    assert 900 not in before and 900 in after
    assert models.find_contestant_id_by_username(conn, "cait") == 900


def test_a_chat_that_does_not_exist_is_unreachable_not_a_failure():
    """The real /announce reported 3 'failures' that were only absent chats."""
    def send(uid, text):
        if uid == 2:
            raise LookupError("chat not found")
        return True

    result = broadcast([1, 2, 3], "hi", send=send)
    assert result.unreachable == 1
    assert result.failed == 0
    assert result.sent == 2
    assert result.total == 3
    assert "لم يبدأوا محادثة البوت" in result.summary_ar()


def test_the_summary_stays_quiet_about_categories_with_nothing_in_them():
    clean = broadcast([1], "hi", send=lambda u, t: True).summary_ar()
    assert "فشل" not in clean and "حظروا" not in clean and "لم يبدأوا" not in clean
