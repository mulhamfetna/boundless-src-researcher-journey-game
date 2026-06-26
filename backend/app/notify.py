import httpx

from app.config import settings


def send_report_dm(user_id: int, text: str, *, token: str | None = None) -> bool:
    tok = settings.bot_token if token is None else token
    if not tok:
        return False
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id": user_id, "text": text},
            timeout=3.0,
        )
        return resp.status_code == 200
    except Exception:
        return False
