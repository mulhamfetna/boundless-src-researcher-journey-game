"""Admin → learner messaging (issue #35).

Telegram rate-limits bulk sending (roughly 30 messages a second) and returns 403
for anyone who has blocked the bot. A naive loop therefore drops messages
silently and stops on the first blocked user — so sending is throttled, every
outcome is counted, and no single failure ends the run.

The send function is injected so the rules can be tested without the network.
"""
import time
from dataclasses import dataclass

from app import models

# Telegram's documented ceiling is ~30 messages/second to different users.
# 20/s leaves headroom for the bot's own traffic.
SEND_INTERVAL_S = 0.05


@dataclass(frozen=True)
class Outcome:
    sent: int = 0
    blocked: int = 0
    failed: int = 0
    # A chat that does not exist — e.g. an id that never messaged the bot. This
    # is NOT a failure: nothing went wrong, there is simply nobody there. Mixing
    # the two made a healthy broadcast look broken (#39).
    unreachable: int = 0

    @property
    def total(self) -> int:
        return self.sent + self.blocked + self.failed + self.unreachable

    def summary_ar(self) -> str:
        return (
            f"تم الإرسال إلى {self.sent} مستخدمًا."
            + (f"\nلم يبدأوا محادثة البوت: {self.unreachable}." if self.unreachable else "")
            + (f"\nحظروا البوت: {self.blocked}." if self.blocked else "")
            + (f"\nفشل الإرسال: {self.failed}." if self.failed else "")
        )


def resolve_recipient(conn, who: str) -> int | None:
    """Accept @username, username, or a numeric id. Returns None if unknown."""
    who = (who or "").strip()
    if not who:
        return None
    if who.lstrip("-").isdigit():
        uid = int(who)
        return uid if models.contestant_exists(conn, uid) else uid
    return models.find_contestant_id_by_username(conn, who.lstrip("@"))


def broadcast(user_ids, text, *, send, sleep=time.sleep) -> Outcome:
    """Send `text` to every id, pausing between messages.

    `send(user_id, text)` should raise PermissionError when the user has blocked
    the bot and LookupError when the chat does not exist; any other exception
    counts as a plain failure. None of them stop the run.
    """
    sent = blocked = failed = unreachable = 0
    ids = list(user_ids)
    for i, uid in enumerate(ids):
        try:
            ok = send(uid, text)
            if ok is False:
                failed += 1
            else:
                sent += 1
        except PermissionError:
            blocked += 1
        except LookupError:
            unreachable += 1
        except Exception:
            failed += 1
        if i < len(ids) - 1:
            sleep(SEND_INTERVAL_S)
    return Outcome(sent=sent, blocked=blocked, failed=failed, unreachable=unreachable)
