from app.scoring import (
    clamp_time, speed_bonus, streak_multiplier, score_answer, grade, score_fraction,
)


def test_clamp_time_bounds():
    assert clamp_time(-5) == 0
    assert clamp_time(70000) == 60000
    assert clamp_time(1234) == 1234


def test_speed_bonus_decays_linearly():
    assert speed_bonus(0) == 50
    assert speed_bonus(60000) == 0
    assert speed_bonus(30000) == 25


def test_streak_multiplier_caps():
    assert streak_multiplier(0) == 1.0
    assert streak_multiplier(3) == 1.3
    assert streak_multiplier(10) == 1.5


def test_score_answer_wrong_is_zero():
    assert score_answer(100, False, 1000, 4) == 0


def test_score_answer_correct_fast_no_streak():
    # base 100 + bonus 50, multiplier 1.0 -> 150
    assert score_answer(100, True, 0, 0) == 150


def test_score_answer_applies_streak_and_clamp():
    # base 100 + bonus 0 (>=window), multiplier 1.2 -> 120
    assert score_answer(100, True, 90000, 2) == 120


def test_grade_mcq_full_and_zero():
    data = {"options_ar": ["a", "b"], "correct_index": 1}
    assert grade("mcq", data, {"index": 1}) == (1.0, True)
    assert grade("mcq", data, {"index": 0}) == (0.0, False)


def test_grade_match_partial():
    data = {"left_ar": ["L0", "L1"], "right_ar": ["R0", "R1"],
            "correct_pairs": [[0, 1], [1, 0]]}
    # one of two pairs right
    frac, full = grade("match", data, {"pairs": [[0, 1], [1, 1]]})
    assert frac == 0.5 and full is False
    frac, full = grade("match", data, {"pairs": [[0, 1], [1, 0]]})
    assert frac == 1.0 and full is True


def test_grade_order_partial():
    data = {"items_ar": ["A", "B", "C"], "correct_sequence": [2, 0, 1]}
    # positions: [2,0,1] correct -> 3/3
    assert grade("order", data, {"sequence": [2, 0, 1]}) == (1.0, True)
    # [2,1,0] -> only position 0 correct -> 1/3
    frac, full = grade("order", data, {"sequence": [2, 1, 0]})
    assert round(frac, 3) == 0.333 and full is False


def test_grade_handles_missing_or_malformed():
    data = {"items_ar": ["A", "B"], "correct_sequence": [0, 1]}
    assert grade("order", data, {}) == (0.0, False)
    data2 = {"left_ar": ["L"], "right_ar": ["R"], "correct_pairs": [[0, 0]]}
    assert grade("match", data2, {"pairs": []}) == (0.0, False)


def test_score_fraction_partial():
    # base 100 + bonus 0 (slow), fraction 0.5, streak 0 -> 50
    assert score_fraction(100, 0.5, 90000, 0) == 50
    # base 100 + bonus 50 (fast), fraction 1.0, streak 0 -> 150
    assert score_fraction(100, 1.0, 0, 0) == 150
