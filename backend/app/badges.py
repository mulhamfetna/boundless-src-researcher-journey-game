import sqlite3

ALL_CODES = ["perfect_capstone", "senior_researcher", "all_stations", "flawless", "streak_10",
             "perfect_quiz", "streak_master", "dedicated", "self_reliant", "first_finish"]
# Rarest/hardest first (drives top_badge display).
_PRIORITY = list(ALL_CODES)
STREAK_MASTER_MIN = 5
STREAK_10_MIN = 10
DEDICATED_MIN = 10  # finished attempts
TOPIC_STATIONS = {"foundations", "journals", "paper-types", "paper-parts", "publishing", "submission"}


def evaluate(summary: dict) -> list[str]:
    codes = []
    perfect_min = summary.get("perfect_min", 0)
    answered = summary.get("answered", perfect_min)
    full = answered >= perfect_min  # a partial submission can't game "perfect"
    accuracy = summary.get("accuracy", 0)
    hints = summary.get("hints_used", 1)
    streak = summary.get("max_streak", 0)
    if accuracy >= 1.0 and full:
        codes.append("perfect_quiz")
    if hints == 0:
        codes.append("self_reliant")
    if streak >= STREAK_MASTER_MIN:
        codes.append("streak_master")
    if summary.get("is_first_finish", False):
        codes.append("first_finish")
    # --- expanded badges ---
    if streak >= STREAK_10_MIN:
        codes.append("streak_10")
    if accuracy >= 1.0 and hints == 0 and full:
        codes.append("flawless")  # perfect AND no hints
    if summary.get("slug") == "capstone" and accuracy >= 1.0 and full:
        codes.append("perfect_capstone")
    return codes


def evaluate_stateful(conn: sqlite3.Connection, contestant_id: int) -> list[str]:
    """Cross-attempt badges computed from the DB (all-stations, dedication)."""
    codes = []
    rows = conn.execute(
        "SELECT DISTINCT q.slug FROM attempts a JOIN quizzes q ON q.id = a.quiz_id "
        "WHERE a.contestant_id = ? AND a.finished_at IS NOT NULL", (contestant_id,)
    ).fetchall()
    done = {r["slug"] for r in rows}
    if TOPIC_STATIONS <= done:
        codes.append("all_stations")
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM attempts WHERE contestant_id = ? AND finished_at IS NOT NULL",
        (contestant_id,),
    ).fetchone()["n"]
    if n >= DEDICATED_MIN:
        codes.append("dedicated")
    return codes


def award(conn: sqlite3.Connection, contestant_id: int, codes: list[str], now: str) -> list[str]:
    new = []
    for code in codes:
        cur = conn.execute(
            "INSERT OR IGNORE INTO badges (contestant_id, code, earned_at) VALUES (?, ?, ?)",
            (contestant_id, code, now),
        )
        if cur.rowcount:
            new.append(code)
    conn.commit()
    return new


def get_badges(conn, contestant_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT code FROM badges WHERE contestant_id = ?", (contestant_id,)
    ).fetchall()
    return [r["code"] for r in rows]


def top_badge(conn, contestant_id: int):
    earned = set(get_badges(conn, contestant_id))
    for code in _PRIORITY:
        if code in earned:
            return code
    return None
