import json

from fastapi import APIRouter, Header, HTTPException, Request

from app import models, badges, notify
from app.auth import validate_init_data, AuthError
from app.config import settings
from app.scoring import grade, score_fraction, speed_bonus

router = APIRouter(prefix="/api")


def _conn(request: Request):
    conn = getattr(request.app.state, "conn", None)
    if conn is None:
        from app.main import _conn as shared  # set at startup
        conn = shared
    return conn


@router.get("/quizzes")
def list_quizzes(request: Request):
    conn = _conn(request)
    rows = conn.execute("SELECT slug, title_ar FROM quizzes ORDER BY display_order, id").fetchall()
    return [{"slug": r["slug"], "title_ar": r["title_ar"]} for r in rows]


@router.get("/quizzes/{slug}/questions")
def get_questions(slug: str, request: Request):
    conn = _conn(request)
    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")
    out = []
    for q in models.get_questions(conn, quiz["id"]):
        data = json.loads(q["data_json"])
        asset = models.get_asset_for_question(conn, q["id"])
        item = {
            "id": q["id"],
            "type": q["type"],
            "prompt_ar": q["prompt_ar"],
            "base_points": q["base_points"],
            "asset_file": asset["file_path"] if asset else None,
        }
        if q["type"] in ("mcq", "tf", "image"):
            item["options_ar"] = data["options_ar"]
        elif q["type"] == "match":
            item["left_ar"] = data["left_ar"]
            item["right_ar"] = data["right_ar"]
        elif q["type"] == "order":
            item["items_ar"] = data["items_ar"]
        out.append(item)
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]}, "questions": out}


@router.post("/quizzes/{slug}/submit")
def submit(slug: str, payload: dict, request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")

    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")

    qrows = {q["id"]: q for q in models.get_questions(conn, quiz["id"])}

    contestant_id = models.upsert_contestant(conn, user)
    is_first_finish = conn.execute(
        "SELECT COUNT(*) AS n FROM attempts WHERE contestant_id=? AND finished_at IS NOT NULL",
        (contestant_id,),
    ).fetchone()["n"] == 0
    attempt_id = models.create_attempt(conn, contestant_id, quiz["id"], "async", _now(conn))

    total = 0
    correct_count = 0
    streak = 0
    max_streak = 0
    bonus_sum = 0
    processed = 0
    answers = payload.get("answers", [])
    for a in answers:
        qid = a.get("question_id")
        q = qrows.get(qid)
        if not q:
            continue
        processed += 1
        data = json.loads(q["data_json"])
        fraction, is_full = grade(q["type"], data, a)
        time_ms = int(a.get("time_ms", 60000))
        pts = score_fraction(q["base_points"], fraction, time_ms, streak)
        bonus_sum += speed_bonus(time_ms)
        streak = streak + 1 if is_full else 0
        max_streak = max(max_streak, streak)
        if is_full:
            correct_count += 1
        total += pts
        models.record_answer(conn, attempt_id, qid, a, is_full, int(a.get("time_ms", 0)), pts)

    accuracy = correct_count / processed if processed else 0.0
    models.finish_attempt(conn, attempt_id, total, accuracy, int(payload.get("duration_ms", 0)), _now(conn))
    models.set_attempt_max_streak(conn, attempt_id, max_streak)

    summary = {
        "accuracy": accuracy,
        "max_streak": max_streak,
        "avg_speed_bonus": (bonus_sum / processed) if processed else 0.0,
        "is_first_finish": is_first_finish,
    }
    earned_now = badges.award(conn, contestant_id, badges.evaluate(summary), _now(conn))

    from app.report import build_report, format_report_text
    report = build_report(conn, attempt_id)
    report["attempt_id"] = attempt_id
    report["earned_now"] = earned_now

    notify.send_report_dm(contestant_id, format_report_text(report, quiz["title_ar"]))
    return report


@router.get("/leaderboard")
def get_leaderboard(request: Request, scope: str = "quiz", slug: str = ""):
    conn = _conn(request)
    if scope == "overall":
        rows = models.leaderboard_overall(conn)
        return [
            {"first_name": r["first_name"], "total_score": r["total_score"],
             "top_badge": badges.top_badge(conn, r["telegram_user_id"])}
            for r in rows
        ]
    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")
    rows = models.leaderboard(conn, quiz["id"])
    return [
        {"first_name": r["first_name"], "best_score": r["best_score"],
         "top_badge": badges.top_badge(conn, r["telegram_user_id"])}
        for r in rows
    ]


@router.get("/me/badges")
def me_badges(request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    return {"badges": badges.get_badges(conn, int(user["id"]))}


def _now(conn):
    return conn.execute("SELECT datetime('now')").fetchone()[0]
