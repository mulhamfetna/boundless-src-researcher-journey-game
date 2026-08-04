"""رحلة الباحث — The Researcher's Journey.

Copyright (C) 2026 Boundless Academic Services, the Scientific Research Camp
initiative, and Mulham Fetna.
Licensed under AGPL-3.0-or-later. See LICENSE and NOTICE.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
import asyncio

from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes

from app import models
from app.broadcast import Outcome, SEND_INTERVAL_S, resolve_recipient

from app.config import settings
from app.db import connect, init_schema
from app.models import get_quiz_by_slug, leaderboard, leaderboard_overall, list_issue_reports


def leaderboard_text(conn, slug: str) -> str:
    quiz = get_quiz_by_slug(conn, slug)
    if not quiz:
        return "لا توجد مسابقة بهذا الاسم."
    rows = leaderboard(conn, quiz["id"])
    if not rows:
        return f"لا نتائج بعد في: {quiz['title_ar']}"
    lines = [f"🏆 لوحة الصدارة — {quiz['title_ar']}"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['first_name']} — {r['best_score']}")
    return "\n".join(lines)


def overall_leaderboard_text(conn) -> str:
    rows = leaderboard_overall(conn)
    if not rows:
        return "لا توجد نتائج بعد. كن أول المتسابقين! 🎮"
    lines = ["🏆 لوحة الصدارة الإجمالية"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['first_name']} — {r['total_score']}")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Register on /start (#35). Contestants used to be created only when an
    # attempt was submitted, so anyone who opened the bot but never finished a
    # station was invisible to /announce — which is meant to reach ALL users.
    user = update.effective_user
    if user:
        conn = connect(settings.db_path)
        init_schema(conn)
        try:
            models.upsert_contestant(conn, {
                "id": user.id, "first_name": user.first_name or "", "username": user.username,
            })
        except Exception:
            pass
        finally:
            conn.close()

    url = settings.public_url.rstrip("/") + "/app/"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("ابدأ المسابقة 🎮", web_app=WebAppInfo(url=url))]])
    await update.message.reply_text("أهلاً بك في مسابقة الجلسات! اضغط للبدء:", reply_markup=kb)


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        await update.message.reply_text(overall_leaderboard_text(conn))
    finally:
        conn.close()


def is_admin(user_id: int, admin_id: int) -> bool:
    return bool(admin_id) and user_id == admin_id


def format_reports(rows) -> str:
    if not rows:
        return "لا توجد بلاغات بعد."
    lines = ["🐞 آخر البلاغات:"]
    for r in rows:
        who = r["first_name"] or "—"
        uname = f" @{r['username']}" if r["username"] else ""
        meta = f"{r['language_code'] or '?'} · {r['platform'] or '?'}"
        lines.append(f"• [{r['created_at']}] {who}{uname} ({meta})\n  {r['text']}")
    return "\n".join(lines)


async def reports_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id, settings.admin_id):
        await update.message.reply_text("هذا الأمر للمشرف فقط.")
        return
    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        await update.message.reply_text(format_reports(list_issue_reports(conn)))
    finally:
        conn.close()


async def announce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/announce <text> — message every user the bot knows (#35)."""
    user = update.effective_user
    if not user or not is_admin(user.id, settings.admin_id):
        await update.message.reply_text("هذا الأمر للمشرف فقط.")
        return
    text = " ".join(context.args or []).strip()
    if not text:
        await update.message.reply_text("الاستخدام: /announce نص الإعلان")
        return

    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        ids = models.all_contestant_ids(conn)
    finally:
        conn.close()
    if not ids:
        await update.message.reply_text("لا يوجد مستخدمون بعد.")
        return

    await update.message.reply_text(f"جارٍ الإرسال إلى {len(ids)} مستخدمًا…")

    async def send(uid, body):
        try:
            await context.bot.send_message(chat_id=uid, text=body)
            return True
        except Forbidden:
            raise PermissionError("blocked")

    outcome = await _broadcast_async(ids, text, send)
    await update.message.reply_text("📣 انتهى الإعلان.\n" + outcome.summary_ar())


async def dm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dm <@username|id> <text> — message one person (#35)."""
    user = update.effective_user
    if not user or not is_admin(user.id, settings.admin_id):
        await update.message.reply_text("هذا الأمر للمشرف فقط.")
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("الاستخدام: /dm @username نص الرسالة")
        return

    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        target = resolve_recipient(conn, args[0])
    finally:
        conn.close()
    if target is None:
        await update.message.reply_text(f"لم أجد المستخدم {args[0]}.")
        return

    body = " ".join(args[1:]).strip()
    try:
        await context.bot.send_message(chat_id=target, text=body)
        await update.message.reply_text(f"✅ أُرسلت إلى {args[0]}.")
    except Forbidden:
        await update.message.reply_text(f"⚠️ {args[0]} حظر البوت، تعذّر الإرسال.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ تعذّر الإرسال: {e}")


async def _broadcast_async(ids, text, send):
    """Async twin of broadcast.broadcast — same counting and throttling rules."""
    sent = blocked = failed = 0
    for i, uid in enumerate(ids):
        try:
            await send(uid, text)
            sent += 1
        except PermissionError:
            blocked += 1
        except Exception:
            failed += 1
        if i < len(ids) - 1:
            await asyncio.sleep(SEND_INTERVAL_S)
    return Outcome(sent=sent, blocked=blocked, failed=failed)


def build_application() -> Application:
    app = Application.builder().token(settings.bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("reports", reports_cmd))
    app.add_handler(CommandHandler("announce", announce_cmd))
    app.add_handler(CommandHandler("dm", dm_cmd))
    return app


def main():
    build_application().run_polling()


if __name__ == "__main__":
    main()
