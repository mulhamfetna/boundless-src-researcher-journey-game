import sqlite3

ALL_CODES = ["perfect_quiz", "speed_demon", "streak_master", "first_finish"]
_PRIORITY = ["perfect_quiz", "streak_master", "speed_demon", "first_finish"]
SPEED_DEMON_MIN_AVG_BONUS = 35.0
STREAK_MASTER_MIN = 5


def evaluate(summary: dict) -> list[str]:
    codes = []
    if summary.get("accuracy", 0) >= 1.0:
        codes.append("perfect_quiz")
    if summary.get("avg_speed_bonus", 0) >= SPEED_DEMON_MIN_AVG_BONUS:
        codes.append("speed_demon")
    if summary.get("max_streak", 0) >= STREAK_MASTER_MIN:
        codes.append("streak_master")
    if summary.get("is_first_finish", False):
        codes.append("first_finish")
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
