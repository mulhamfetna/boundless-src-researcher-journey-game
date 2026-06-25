from app.scoring import (
    clamp_time, speed_bonus, streak_multiplier, score_answer,
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
