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
