import json


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
        items.append({
            "prompt_ar": q["prompt_ar"],
            "options_ar": data["options_ar"],
            "correct_index": data["correct_index"],
            "given_index": json.loads(ans["given_json"]).get("index"),
            "is_correct": bool(ans["is_correct"]),
            "explanation_ar": q["explanation_ar"],
            "source_page": q["source_page"],
            "asset_file": asset["file_path"] if asset else None,
        })

    rank_row = conn.execute(
        """SELECT COUNT(*) + 1 AS rank FROM (
               SELECT a.contestant_id, MAX(a.total_score) AS best
               FROM attempts a WHERE a.quiz_id = ? AND a.finished_at IS NOT NULL
               GROUP BY a.contestant_id
           ) WHERE best > ?""",
        (attempt["quiz_id"], attempt["total_score"]),
    ).fetchone()

    return {
        "total_score": attempt["total_score"],
        "accuracy": attempt["accuracy"],
        "duration_ms": attempt["duration_ms"],
        "rank": rank_row["rank"],
        "items": items,
    }


def format_report_text(report: dict, title_ar: str) -> str:
    correct = sum(1 for it in report["items"] if it["is_correct"])
    total = len(report["items"])
    pct = round(report["accuracy"] * 100)
    return (
        f"🏁 نتيجتك في: {title_ar}\n"
        f"النقاط: {report['total_score']}\n"
        f"الإجابات الصحيحة: {correct}/{total} ({pct}%)\n"
        f"الترتيب: #{report['rank']}"
    )
