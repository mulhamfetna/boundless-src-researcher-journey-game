import app.notify as notify


def test_disabled_when_no_token():
    assert notify.send_report_dm(1, "hi", token="") is False


def test_success(monkeypatch):
    calls = {}

    class FakeResp:
        status_code = 200

    def fake_post(url, json, timeout):
        calls["url"] = url
        calls["json"] = json
        return FakeResp()

    monkeypatch.setattr(notify.httpx, "post", fake_post)
    ok = notify.send_report_dm(42, "نتيجتك", token="123:ABC")
    assert ok is True
    assert "sendMessage" in calls["url"] and calls["json"]["chat_id"] == 42


def test_never_raises_on_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(notify.httpx, "post", boom)
    assert notify.send_report_dm(42, "x", token="123:ABC") is False
