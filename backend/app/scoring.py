def clamp_time(time_ms: int) -> int:
    return max(0, min(int(time_ms), 60000))


def speed_bonus(time_ms: int, max_bonus: int = 50, window_ms: int = 60000) -> int:
    t = clamp_time(time_ms)
    if t >= window_ms:
        return 0
    return round(max_bonus * (1 - t / window_ms))


def streak_multiplier(streak: int) -> float:
    return round(1.0 + 0.1 * min(max(streak, 0), 5), 2)


def score_answer(base_points: int, is_correct: bool, time_ms: int, streak_before: int) -> int:
    if not is_correct:
        return 0
    raw = (base_points + speed_bonus(time_ms)) * streak_multiplier(streak_before)
    return round(raw)


def score_fraction(base_points: int, fraction: float, time_ms: int, streak_before: int) -> int:
    if fraction <= 0:
        return 0
    raw = (base_points + speed_bonus(time_ms)) * fraction * streak_multiplier(streak_before)
    return round(raw)


def grade(qtype: str, data: dict, given: dict) -> tuple[float, bool]:
    if qtype in ("mcq", "tf", "image"):
        gi = given.get("index")
        try:
            ok = gi is not None and int(gi) == data["correct_index"]
        except (ValueError, TypeError):
            ok = False
        return (1.0, True) if ok else (0.0, False)

    if qtype == "match":
        correct = {tuple(p) for p in data["correct_pairs"]}
        given_pairs = {tuple(p) for p in given.get("pairs", [])}
        if not correct:
            return (0.0, False)
        frac = len(given_pairs & correct) / len(correct)
        return (frac, frac == 1.0)

    if qtype == "order":
        seq = data["correct_sequence"]
        given_seq = given.get("sequence", [])
        if len(given_seq) != len(seq) or not seq:
            return (0.0, False)
        placed = sum(1 for i, v in enumerate(seq) if given_seq[i] == v)
        frac = placed / len(seq)
        return (frac, frac == 1.0)

    return (0.0, False)
