from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.db import connect, init_schema
from app.models import get_quiz_by_slug, leaderboard


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = settings.public_url.rstrip("/") + "/app/"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("ابدأ المسابقة 🎮", web_app=WebAppInfo(url=url))]])
    await update.message.reply_text("أهلاً بك في مسابقة الجلسات! اضغط للبدء:", reply_markup=kb)


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        await update.message.reply_text(leaderboard_text(conn, "journals"))
    finally:
        conn.close()


def build_application() -> Application:
    app = Application.builder().token(settings.bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    return app


def main():
    build_application().run_polling()


if __name__ == "__main__":
    main()
