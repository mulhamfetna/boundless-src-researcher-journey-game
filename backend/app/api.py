import json

from fastapi import APIRouter, Header, HTTPException, Request

from app import models
from app.auth import validate_init_data, AuthError
from app.config import settings
from app.scoring import score_answer

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
        out.append({
            "id": q["id"],
            "type": q["type"],
            "prompt_ar": q["prompt_ar"],
            "options_ar": data["options_ar"],
            "base_points": q["base_points"],
            "asset_file": asset["file_path"] if asset else None,
        })
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

    correct_by_id = {}
    base_by_id = {}
    for q in models.get_questions(conn, quiz["id"]):
        correct_by_id[q["id"]] = json.loads(q["data_json"])["correct_index"]
        base_by_id[q["id"]] = q["base_points"]

    contestant_id = models.upsert_contestant(conn, user)
    attempt_id = models.create_attempt(conn, contestant_id, quiz["id"], "async", _now(conn))

    total = 0
    correct_count = 0
    streak = 0
    answers = payload.get("answers", [])
    for a in answers:
        qid = a["question_id"]
        if qid not in correct_by_id:
            continue
        is_correct = int(a.get("index")) == correct_by_id[qid]
        pts = score_answer(base_by_id[qid], is_correct, int(a.get("time_ms", 60000)), streak)
        streak = streak + 1 if is_correct else 0
        if is_correct:
            correct_count += 1
        total += pts
        models.record_answer(conn, attempt_id, qid, {"index": a.get("index")}, is_correct, int(a.get("time_ms", 0)), pts)

    accuracy = correct_count / len(answers) if answers else 0.0
    models.finish_attempt(conn, attempt_id, total, accuracy, int(payload.get("duration_ms", 0)), _now(conn))

    from app.report import build_report
    report = build_report(conn, attempt_id)
    report["attempt_id"] = attempt_id
    return report


@router.get("/leaderboard")
def get_leaderboard(slug: str, request: Request):
    conn = _conn(request)
    quiz = models.get_quiz_by_slug(conn, slug)
    if not quiz:
        raise HTTPException(404, "quiz not found")
    rows = models.leaderboard(conn, quiz["id"])
    return [{"first_name": r["first_name"], "best_score": r["best_score"]} for r in rows]


def _now(conn):
    return conn.execute("SELECT datetime('now')").fetchone()[0]
