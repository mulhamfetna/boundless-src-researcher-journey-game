import json
import random

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app import models, badges, notify, progress
from app.auth import validate_init_data, AuthError
from app.config import settings
from app.sampling import sample_questions
from app.scoring import score_retry

router = APIRouter(prefix="/api")

# Journey quizzes play in authored order (no sampling) and award the pinnacle badge.
JOURNEY_SLUGS = {"capstone"}


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
    funfacts = json.loads(quiz["fun_facts_json"]) if quiz["fun_facts_json"] else []
    for q in models.get_questions(conn, quiz["id"]):
        data = json.loads(q["data_json"])
        asset = models.get_asset_for_question(conn, q["id"])
        item = {
            "id": q["id"], "type": q["type"], "prompt_ar": q["prompt_ar"],
            "base_points": q["base_points"], "asset_file": asset["file_path"] if asset else None,
            "hint_ar": data.get("hint_ar", ""), "concept": data.get("concept", ""),
            "passage": data.get("passage", ""), "source_url": data.get("source_url", ""),
        }
        if q["type"] in ("mcq", "tf", "image"):
            item["options_ar"] = data["options_ar"]
            item["correct_index"] = data["correct_index"]
            item["option_explanations_ar"] = data.get("option_explanations_ar", [])
        elif q["type"] == "match":
            item["left_ar"] = data["left_ar"]; item["right_ar"] = data["right_ar"]
            item["correct_pairs"] = data["correct_pairs"]
        elif q["type"] == "order":
            item["items_ar"] = data["items_ar"]; item["correct_sequence"] = data["correct_sequence"]
        elif q["type"] == "spot":
            item["options_ar"] = data["options_ar"]
            item["correct_indices"] = data["correct_indices"]
            item["chip_explanations_ar"] = data.get("chip_explanations_ar", [])
        out.append(item)
    # Journey quizzes (the capstone) play their authored stages IN ORDER; everyone
    # else gets a concept-balanced random sample.
    sampled = out if slug in JOURNEY_SLUGS else sample_questions(out, settings.sample_size, random.Random())
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]},
            "questions": sampled, "fun_facts_ar": funfacts}


@router.post("/quizzes/{slug}/submit")
def submit(slug: str, payload: dict, request: Request, background_tasks: BackgroundTasks, x_init_data: str = Header(default="")):
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
    first_try_count = 0
    streak = 0
    max_streak = 0
    hints_used = 0
    answers = payload.get("answers", [])
    for a in answers:
        qid = a.get("question_id")
        q = qrows.get(qid)
        if not q:
            continue
        retries = int(a.get("retries", 0))
        hint_used = bool(a.get("hint_used", False))
        first_try = retries == 0 and not hint_used
        pts = score_retry(q["base_points"], retries, hint_used, streak)
        streak = streak + 1 if first_try else 0
        max_streak = max(max_streak, streak)
        if first_try:
            first_try_count += 1
        if hint_used:
            hints_used += 1
        total += pts
        models.record_answer(conn, attempt_id, qid, {"retries": retries, "hint_used": hint_used},
                             True, 0, pts, retries=retries, hint_used=int(hint_used))

    answered = len(answers)
    accuracy = first_try_count / answered if answered else 0.0
    models.finish_attempt(conn, attempt_id, total, accuracy, int(payload.get("duration_ms", 0)), _now(conn))
    models.set_attempt_max_streak(conn, attempt_id, max_streak)

    perfect_min = min(settings.sample_size, len(qrows))
    summary = {"accuracy": accuracy, "max_streak": max_streak,
               "hints_used": hints_used, "is_first_finish": is_first_finish,
               "answered": answered, "perfect_min": perfect_min}
    summary["slug"] = slug
    codes = badges.evaluate(summary)
    if slug in JOURNEY_SLUGS:  # completing the capstone journey earns the pinnacle badge
        codes = [*codes, "senior_researcher"]
    codes += badges.evaluate_stateful(conn, contestant_id)
    earned_now = badges.award(conn, contestant_id, codes, _now(conn))

    from app.report import build_report, format_report_text
    report = build_report(conn, attempt_id)
    report["attempt_id"] = attempt_id
    report["earned_now"] = earned_now

    background_tasks.add_task(notify.send_report_dm, contestant_id, format_report_text(report, quiz["title_ar"]))
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


@router.get("/me/dashboard")
def me_dashboard(request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    uid = int(user["id"])

    answers = models.get_contestant_answers(conn, uid)
    attempts = models.get_contestant_attempts(conn, uid)
    qoc = models.quiz_of_concept(conn)

    raw_mastery = progress.mastery_for_concepts(answers)
    full_mastery = {}
    mastery_list = []
    for concept, q in qoc.items():
        m = raw_mastery.get(concept, {"rate": 0.0, "count": 0, "level": "not_started"})
        full_mastery[concept] = m
        mastery_list.append({
            "concept": concept,
            "label_ar": progress.CONCEPT_LABELS_AR.get(concept, concept),
            "quiz_slug": q["quiz_slug"],
            "quiz_title_ar": q["quiz_title_ar"],
            "level": m["level"],
            "rate": round(m["rate"], 2),
            "count": m["count"],
        })

    stats = progress.summarize_stats(attempts)
    stats["hints_used"] = sum(1 for a in answers if a["hint_used"])

    return {
        "stats": stats,
        "mastery": mastery_list,
        "history": attempts[:15],
        "next": progress.next_steps(full_mastery, qoc),
        "badges": badges.get_badges(conn, uid),
    }


@router.post("/report")
def report(payload: dict, request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "empty report")

    models.insert_issue_report(conn, {
        "telegram_user_id": int(user["id"]),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "language_code": user.get("language_code"),
        "is_premium": int(bool(user.get("is_premium"))),
        "allows_write_to_pm": int(bool(user.get("allows_write_to_pm"))),
        "auth_date": parsed.get("auth_date"),
        "chat_type": parsed.get("chat_type"),
        "chat_instance": parsed.get("chat_instance"),
        "query_id": parsed.get("query_id"),
        "start_param": parsed.get("start_param"),
        "platform": payload.get("platform"),
        "app_version": payload.get("version"),
        "text": text,
        "raw_json": json.dumps(parsed, ensure_ascii=False),
    })
    return {"ok": True}


def _now(conn):
    return conn.execute("SELECT datetime('now')").fetchone()[0]
