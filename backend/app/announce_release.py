"""Announce a new release to players (issue #41).

Run by the deploy job AFTER the smoke test, so an announcement can only go out
for a release that is genuinely live. Three rules keep it from becoming noise or
a liability:

  * **Selective** — minor/major versions speak; patches stay quiet unless the
    release notes contain `[announce]`. Announcing every one-line fix teaches
    people to ignore announcements.
  * **Once** — the tag is recorded in `meta`, so re-running a workflow (which
    happened when a release hit a GitHub rate limit) cannot double-send.
  * **Never fatal** — `main()` swallows everything. A messaging problem must not
    roll back a healthy deploy.

Usage (inside the web container, on the server):
    RELEASE_TAG=v1.5.0 RELEASE_TITLE="..." RELEASE_NOTES="..." python -m app.announce_release
"""
import os
import re
import sys

from app import models
from app.broadcast import broadcast
from app.config import settings
from app.db import connect, init_schema
from app.notify import send_report_dm

OPT_IN_MARKER = "[announce]"
_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def should_announce(tag: str, notes: str = "") -> bool:
    """Minor/major speak; patches stay quiet unless they opt in."""
    if OPT_IN_MARKER in (notes or ""):
        return True
    m = _SEMVER.match((tag or "").strip())
    if not m:
        return False          # unparseable tag: stay quiet rather than spam
    _, _, patch = m.groups()
    return patch == "0"


def compose_message(tag: str, title: str = "") -> str:
    """The reassurance is the point: people fear an update wipes their score."""
    headline = f"🎉 صدر تحديث جديد للعبة: {tag}"
    if title:
        headline += f"\n{title}"
    return (
        headline
        + "\n\nاضغط /start ثم افتح اللعبة للاستفادة من التحديث."
        + "\n\n✅ تقدّمك ونقاطك وأوسمتك محفوظة بالكامل — لن تفقد شيئًا."
    )


def already_announced(conn, tag: str) -> bool:
    row = conn.execute("SELECT 1 FROM meta WHERE key = ?", (f"announced:{tag}",)).fetchone()
    return row is not None


def mark_announced(conn, tag: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (f"announced:{tag}",),
    )
    conn.commit()


def main() -> int:
    tag = os.environ.get("RELEASE_TAG", "").strip()
    title = os.environ.get("RELEASE_TITLE", "").strip()
    notes = os.environ.get("RELEASE_NOTES", "")

    if not tag:
        print("announce: no RELEASE_TAG, nothing to do")
        return 0
    if not should_announce(tag, notes):
        print(f"announce: {tag} is a patch without {OPT_IN_MARKER} — staying quiet")
        return 0

    conn = connect(settings.db_path)
    init_schema(conn)
    if already_announced(conn, tag):
        print(f"announce: {tag} was already announced — not sending again")
        return 0

    ids = models.all_contestant_ids(conn)
    if not ids:
        print("announce: no users yet")
        return 0

    outcome = broadcast(ids, compose_message(tag, title), send=_send)
    mark_announced(conn, tag)
    print(f"announce: {tag} -> sent={outcome.sent} unreachable={outcome.unreachable} "
          f"blocked={outcome.blocked} failed={outcome.failed}")

    if settings.admin_id:
        try:
            send_report_dm(settings.admin_id, f"📣 أُعلن عن {tag}.\n" + outcome.summary_ar())
        except Exception:
            pass
    return 0


def _send(user_id: int, text: str) -> bool:
    """Raises LookupError for a chat that does not exist, PermissionError if blocked."""
    import httpx

    resp = httpx.post(
        f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
        json={"chat_id": user_id, "text": text},
        timeout=5.0,
    )
    if resp.status_code == 200:
        return True
    body = resp.text.lower()
    if "chat not found" in body or "user not found" in body:
        raise LookupError("chat not found")
    if "blocked" in body or "forbidden" in body:
        raise PermissionError("blocked by user")
    return False


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:            # never fail the deploy over an announcement
        print(f"announce: skipped after an error ({e})")
        sys.exit(0)
