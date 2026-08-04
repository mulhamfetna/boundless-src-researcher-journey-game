import json
import random
import secrets

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app import models, badges, notify, progress
from app.auth import validate_init_data, AuthError
from app.config import settings
from app.sampling import sample_questions
from app.scoring import score_retry

router = APIRouter(prefix="/api")

# Journey quizzes play in authored order (no sampling) and award the pinnacle badge.
JOURNEY_SLUGS = {"capstone"}


def _serialize_question(conn, q) -> dict:
    """Public (answer-key-inclusive) shape of a question row for the runner."""
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
    return item


def duel_winner(c_correct, c_time, o_correct, o_time):
    """A correct answer beats a wrong one; among equals, the faster time wins."""
    c_correct, o_correct = bool(c_correct), bool(o_correct)
    if c_correct != o_correct:
        return "creator" if c_correct else "opponent"
    if (c_time or 0) < (o_time or 0):
        return "creator"
    if (o_time or 0) < (c_time or 0):
        return "opponent"
    return "tie"


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
        out.append(_serialize_question(conn, q))
    # Journey quizzes (the capstone) play their authored stages IN ORDER; everyone
    # else gets a concept-balanced random sample.
    sampled = out if slug in JOURNEY_SLUGS else sample_questions(out, settings.sample_size, random.Random())
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]},
            "questions": sampled, "fun_facts_ar": funfacts}


@router.get("/me/review")
def me_review(request: Request, x_init_data: str = Header(default="")):
    """Hex-Recall: ~5 questions drawn from the player's weakest concepts (practice, no scoring)."""
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    uid = int(user["id"])
    mastery = progress.mastery_for_concepts(models.get_contestant_answers(conn, uid))
    weak = {c for c, m in mastery.items() if m.get("level") != "mastered"}
    pool = [
        _serialize_question(conn, q)
        for quiz in conn.execute("SELECT id FROM quizzes").fetchall()
        for q in models.get_questions(conn, quiz["id"])
    ]
    focus = [q for q in pool if q["concept"] in weak] if weak else pool
    if not focus:
        focus = pool
    random.Random().shuffle(focus)
    return {"questions": focus[: min(5, len(focus))]}


@router.post("/duels")
def duel_create(payload: dict, request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    qid = payload.get("question_id")
    if not models.get_question(conn, qid):
        raise HTTPException(404, "question not found")
    cid = models.upsert_contestant(conn, user)
    token = secrets.token_urlsafe(6)
    models.create_duel(conn, token, qid, cid, bool(payload.get("correct")), int(payload.get("time_ms", 0)), _now(conn))
    return {"token": token, "link": f"https://t.me/{settings.bot_username}?startapp=duel_{token}"}


@router.get("/duels/{token}")
def duel_get(token: str, request: Request):
    conn = _conn(request)
    d = models.get_duel(conn, token)
    if not d:
        raise HTTPException(404, "duel not found")
    q = models.get_question(conn, d["question_id"])
    if not q:
        raise HTTPException(404, "question gone")
    return {
        "token": token, "status": d["status"],
        "question": _serialize_question(conn, q),
        "creator": {"name": models.contestant_name(conn, d["creator_id"]),
                    "correct": bool(d["creator_correct"]), "time_ms": d["creator_time_ms"]},
    }


@router.post("/duels/{token}/answer")
def duel_answer(token: str, payload: dict, request: Request, background_tasks: BackgroundTasks, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    d = models.get_duel(conn, token)
    if not d:
        raise HTTPException(404, "duel not found")
    oid = models.upsert_contestant(conn, user)
    just_finished = d["status"] == "open" and d["opponent_id"] is None
    if just_finished:
        models.finish_duel(conn, token, oid, bool(payload.get("correct")), int(payload.get("time_ms", 0)))
        d = models.get_duel(conn, token)
    winner = duel_winner(d["creator_correct"], d["creator_time_ms"], d["opponent_correct"], d["opponent_time_ms"])
    cname = models.contestant_name(conn, d["creator_id"])
    oname = models.contestant_name(conn, d["opponent_id"])
    if just_finished:
        wtxt = "تعادل!" if winner == "tie" else ("الفائز: " + (cname if winner == "creator" else oname))
        txt = (f"⚔️ نتيجة المبارزة — {wtxt}\n"
               f"{cname}: {'✅' if d['creator_correct'] else '❌'} ({d['creator_time_ms']}ms)\n"
               f"{oname}: {'✅' if d['opponent_correct'] else '❌'} ({d['opponent_time_ms']}ms)")
        background_tasks.add_task(notify.send_report_dm, d["creator_id"], txt)
        background_tasks.add_task(notify.send_report_dm, d["opponent_id"], txt)
    return {
        "token": token, "winner": winner,
        "creator": {"name": cname, "correct": bool(d["creator_correct"]), "time_ms": d["creator_time_ms"]},
        "opponent": {"name": oname, "correct": bool(d["opponent_correct"]), "time_ms": d["opponent_time_ms"]},
    }


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
        # Skipping (#29) costs everything for that question: retrying floors at
        # 10% of base, so without an explicit zero, skipping would be the cheap
        # way out. It also never counts as a first try, so the streak breaks and
        # accuracy drops.
        skipped = bool(a.get("skipped", False))
        first_try = (not skipped) and retries == 0 and not hint_used
        pts = 0 if skipped else score_retry(q["base_points"], retries, hint_used, streak)
        streak = streak + 1 if first_try else 0
        max_streak = max(max_streak, streak)
        if first_try:
            first_try_count += 1
        if hint_used:
            hints_used += 1
        total += pts
        models.record_answer(conn, attempt_id, qid,
                             {"retries": retries, "hint_used": hint_used, "skipped": skipped},
                             not skipped, 0, pts, retries=retries, hint_used=int(hint_used),
                             skipped=int(skipped))

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
    if scope == "season":
        rows = models.leaderboard_season(conn)
        def _tier(i):
            return "🏛️ عميد المجلس" if i < 3 else ("🎓 زميل بيلتوفر" if i < 10 else "🔬 باحث صاعد")
        return [
            {"first_name": r["first_name"], "total_score": r["total_score"], "tier_ar": _tier(i),
             "top_badge": badges.top_badge(conn, r["telegram_user_id"])}
            for i, r in enumerate(rows)
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
def report(payload: dict, request: Request, background_tasks: BackgroundTasks, x_init_data: str = Header(default="")):
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

    # Push it to the admin (#34). Storing a report and telling nobody meant
    # reports were effectively lost — the admin had no reason to run /reports.
    # Sent in the background so the learner's request is never delayed, and
    # wrapped so a Telegram outage cannot fail their submission.
    if settings.admin_id:
        who = user.get("first_name") or "مستخدم"
        handle = f" (@{user['username']})" if user.get("username") else ""
        meta = " · ".join(filter(None, [payload.get("platform"), payload.get("version")]))
        note = (
            "🐞 بلاغ جديد من داخل التطبيق\n"
            f"من: {who}{handle} — id {user['id']}\n"
            + (f"المنصّة: {meta}\n" if meta else "")
            + f"\n{text}"
        )
        background_tasks.add_task(_notify_admin_safely, settings.admin_id, note)

    return {"ok": True}


def _notify_admin_safely(admin_id: int, text: str) -> None:
    """Never let a delivery problem surface as a failed learner request."""
    try:
        notify.send_report_dm(admin_id, text)
    except Exception:
        pass


def _now(conn):
    return conn.execute("SELECT datetime('now')").fetchone()[0]
