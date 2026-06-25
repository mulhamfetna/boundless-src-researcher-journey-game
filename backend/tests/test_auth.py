import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.auth import validate_init_data, AuthError

BOT_TOKEN = "123456:TESTTOKEN"


def _make_init_data(user: dict, token: str = BOT_TOKEN) -> str:
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    data_check_string = "\n".join(
        f"{k}={fields[k]}" for k in sorted(fields)
    )
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


def test_valid_init_data_returns_user():
    raw = _make_init_data({"id": 42, "first_name": "Lina"})
    parsed = validate_init_data(raw, BOT_TOKEN)
    assert parsed["user"]["id"] == 42
    assert parsed["user"]["first_name"] == "Lina"


def test_tampered_hash_rejected():
    raw = _make_init_data({"id": 42, "first_name": "Lina"})
    tampered = raw.replace("Lina", "Evil")
    with pytest.raises(AuthError):
        validate_init_data(tampered, BOT_TOKEN)


def test_missing_hash_rejected():
    with pytest.raises(AuthError):
        validate_init_data("auth_date=1700000000", BOT_TOKEN)
