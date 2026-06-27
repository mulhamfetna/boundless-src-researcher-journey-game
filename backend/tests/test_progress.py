from app.progress import (
    first_try_of, level_for, mastery_for_concepts, summarize_stats,
    next_steps, CONCEPT_LABELS_AR,
)


def test_first_try_of():
    assert first_try_of({"retries": 0, "hint_used": 0}) is True
    assert first_try_of({"retries": 1, "hint_used": 0}) is False
    assert first_try_of({"retries": 0, "hint_used": 1}) is False


def test_level_for_boundaries():
    assert level_for(0.0, 0) == "not_started"
    assert level_for(0.0, 2) == "familiar"
    assert level_for(0.49, 5) == "familiar"
    assert level_for(0.50, 5) == "proficient"
    assert level_for(0.84, 5) == "proficient"
    assert level_for(0.85, 3) == "mastered"
    assert level_for(1.0, 2) == "proficient"  # >=0.85 but <3 answers -> not mastered


def _ans(concept, order, retries=0, hint=0):
    return {"concept": concept, "order": order, "retries": retries, "hint_used": hint}


def test_mastery_uses_only_recent_n():
    # 6 answers for concept 'x': 5 oldest wrong, 1 newest right -> recent 5 = 4 wrong + 1 right
    answers = [_ans("x", i, retries=1) for i in range(5)] + [_ans("x", 5, retries=0)]
    m = mastery_for_concepts(answers, recent_n=5)["x"]
    assert m["count"] == 5
    assert abs(m["rate"] - 0.2) < 1e-9  # 1 of last 5 first-try
    assert m["level"] == "familiar"


def test_mastery_mastered_when_recent_all_first_try():
    answers = [_ans("y", i) for i in range(4)]  # all first-try
    m = mastery_for_concepts(answers)["y"]
    assert m["level"] == "mastered"


def test_summarize_stats_empty():
    s = summarize_stats([])
    assert s == {"total_points": 0, "attempts_count": 0, "best_by_quiz": {},
                 "best_streak": 0, "first_try_accuracy": 0.0}


def test_summarize_stats_aggregates():
    attempts = [
        {"quiz_slug": "a", "total_score": 100, "accuracy": 0.8, "max_streak": 3},
        {"quiz_slug": "a", "total_score": 150, "accuracy": 1.0, "max_streak": 5},
        {"quiz_slug": "b", "total_score": 60, "accuracy": 0.6, "max_streak": 2},
    ]
    s = summarize_stats(attempts)
    assert s["total_points"] == 310
    assert s["attempts_count"] == 3
    assert s["best_by_quiz"] == {"a": 150, "b": 60}
    assert s["best_streak"] == 5
    assert abs(s["first_try_accuracy"] - 0.8) < 1e-9


def test_next_steps_picks_weakest_then_not_started():
    mastery = {
        "indexing": {"level": "familiar", "rate": 0.2, "count": 5},
        "metrics": {"level": "proficient", "rate": 0.6, "count": 5},
        "quartiles": {"level": "not_started", "rate": 0.0, "count": 0},
    }
    qoc = {
        "indexing": {"quiz_slug": "journals", "quiz_title_ar": "المجلات"},
        "metrics": {"quiz_slug": "journals", "quiz_title_ar": "المجلات"},
        "quartiles": {"quiz_slug": "journals", "quiz_title_ar": "المجلات"},
    }
    out = next_steps(mastery, qoc, limit=2)
    assert [o["concept"] for o in out] == ["indexing", "metrics"]
    assert out[0]["label_ar"] == CONCEPT_LABELS_AR["indexing"]


def test_next_steps_falls_back_to_not_started_when_few_weak():
    mastery = {
        "indexing": {"level": "familiar", "rate": 0.2, "count": 5},
        "quartiles": {"level": "not_started", "rate": 0.0, "count": 0},
    }
    qoc = {"indexing": {"quiz_slug": "j", "quiz_title_ar": "ج"},
           "quartiles": {"quiz_slug": "j", "quiz_title_ar": "ج"}}
    out = next_steps(mastery, qoc, limit=2)
    assert [o["concept"] for o in out] == ["indexing", "quartiles"]


def test_concept_labels_cover_known_slugs():
    for slug in ("predatory_signs", "indexing", "abstract", "research_gap", "review_types"):
        assert slug in CONCEPT_LABELS_AR
