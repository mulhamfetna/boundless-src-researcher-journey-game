import json

_BADGE_AR = {
    "perfect_quiz": "🏅الإتقان",
    "self_reliant": "🛡️بلا تلميحات",
    "streak_master": "🔥السلسلة",
    "first_finish": "🌟البداية",
}


def build_report(conn, attempt_id: int) -> dict:
    attempt = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    answers = conn.execute(
        "SELECT * FROM answers WHERE attempt_id = ? ORDER BY id", (attempt_id,)
    ).fetchall()

    items = []
    for ans in answers:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (ans["question_id"],)).fetchone()
        data = json.loads(q["data_json"])
        asset = conn.execute(
            "SELECT file_path FROM assets WHERE question_id = ? LIMIT 1", (q["id"],)
        ).fetchone()

        _, correct_ar = _describe(q["type"], data, {})
        items.append({
            "type": q["type"], "prompt_ar": q["prompt_ar"], "is_correct": bool(ans["is_correct"]),
            "correct_ar": correct_ar, "retries": ans["retries"], "hint_used": bool(ans["hint_used"]),
            "first_try": ans["retries"] == 0 and not ans["hint_used"],
            "explanation_ar": q["explanation_ar"], "source_page": q["source_page"],
            "asset_file": asset["file_path"] if asset else None,
            "passage": data.get("passage", ""), "source_url": data.get("source_url", ""),
        })

    rank_row = conn.execute(
        """SELECT COUNT(*) + 1 AS rank FROM (
               SELECT a.contestant_id, MAX(a.total_score) AS best
               FROM attempts a WHERE a.quiz_id = ? AND a.finished_at IS NOT NULL
               GROUP BY a.contestant_id
           ) WHERE best > ?""",
        (attempt["quiz_id"], attempt["total_score"]),
    ).fetchone()

    from app.badges import get_badges
    return {
        "total_score": attempt["total_score"],
        "accuracy": attempt["accuracy"],
        "duration_ms": attempt["duration_ms"],
        "max_streak": attempt["max_streak"],
        "rank": rank_row["rank"],
        "items": items,
        "all_badges": get_badges(conn, attempt["contestant_id"]),
    }


def _describe(qtype, data, given):
    """Return (your_ar, correct_ar) human-readable answer strings."""
    if qtype in ("mcq", "tf", "image"):
        opts = data["options_ar"]
        gi = given.get("index")
        your = opts[gi] if isinstance(gi, int) and 0 <= gi < len(opts) else "—"
        return your, opts[data["correct_index"]]
    if qtype == "match":
        left, right = data["left_ar"], data["right_ar"]
        correct = "، ".join(f"{left[li]}↔{right[ri]}" for li, ri in data["correct_pairs"])
        gp = given.get("pairs", [])
        your = "، ".join(f"{left[li]}↔{right[ri]}" for li, ri in gp if 0 <= li < len(left) and 0 <= ri < len(right)) or "—"
        return your, correct
    if qtype == "order":
        items = data["items_ar"]
        correct = " ← ".join(items[i] for i in data["correct_sequence"])
        gs = given.get("sequence", [])
        your = " ← ".join(items[i] for i in gs if 0 <= i < len(items)) or "—"
        return your, correct
    return "—", "—"


def format_report_text(report: dict, title_ar: str) -> str:
    correct = sum(1 for it in report["items"] if it.get("first_try"))
    total = len(report["items"])
    pct = round(report["accuracy"] * 100)
    lines = [
        f"🏁 نتيجتك في: {title_ar}",
        f"النقاط: {report['total_score']}",
        f"الإجابات الصحيحة: {correct}/{total} ({pct}%)",
        f"الترتيب: #{report['rank']}",
    ]
    if report.get("all_badges"):
        lines.append("الأوسمة: " + " ".join(_BADGE_AR.get(b, b) for b in report["all_badges"]))
    return "\n".join(lines)
