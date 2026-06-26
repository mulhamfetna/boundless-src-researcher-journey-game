import json
import sqlite3

from app.content_schema import validate_quiz


def seed_quiz(conn: sqlite3.Connection, doc: dict) -> int:
    validate_quiz(doc)

    existing = conn.execute(
        "SELECT id FROM quizzes WHERE slug = ?", (doc["slug"],)
    ).fetchone()
    if existing:
        qid = existing["id"]
        conn.execute("DELETE FROM assets WHERE quiz_id = ?", (qid,))
        conn.execute("DELETE FROM questions WHERE quiz_id = ?", (qid,))
        conn.execute("DELETE FROM quizzes WHERE id = ?", (qid,))

    cur = conn.execute(
        "INSERT INTO quizzes (slug, title_ar, pdf_filename, display_order) VALUES (?, ?, ?, ?)",
        (doc["slug"], doc["title_ar"], doc["pdf_filename"], doc.get("display_order", 0)),
    )
    quiz_id = cur.lastrowid

    for order, q in enumerate(doc["questions"]):
        if q["type"] in ("mcq", "tf", "image"):
            data = {"options_ar": q["options_ar"], "correct_index": q["correct_index"]}
        elif q["type"] == "match":
            data = {"left_ar": q["left_ar"], "right_ar": q["right_ar"], "correct_pairs": q["correct_pairs"]}
        elif q["type"] == "order":
            data = {"items_ar": q["items_ar"], "correct_sequence": q["correct_sequence"]}
        else:
            data = {}
        qcur = conn.execute(
            """INSERT INTO questions
               (quiz_id, type, prompt_ar, base_points, explanation_ar, source_page, data_json, display_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                quiz_id, q["type"], q["prompt_ar"], q.get("base_points", 100),
                q.get("explanation_ar", ""), q.get("source_page"),
                json.dumps(data, ensure_ascii=False), order,
            ),
        )
        question_id = qcur.lastrowid
        if "asset" in q:
            a = q["asset"]
            conn.execute(
                """INSERT INTO assets
                   (quiz_id, question_id, file_path, kind, source_url, anonymized, caption_ar)
                   VALUES (?, ?, ?, 'image', ?, ?, ?)""",
                (
                    quiz_id, question_id, a["file"], a["source_url"],
                    int(a.get("anonymized", False)), a.get("caption_ar", ""),
                ),
            )
    conn.commit()
    return quiz_id


def seed_from_file(conn: sqlite3.Connection, path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return seed_quiz(conn, json.load(f))
