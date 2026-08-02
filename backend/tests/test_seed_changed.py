"""Per-quiz content hashing.

Seeding a quiz deletes its attempts (see seed.seed_quiz), so an unconditional
reseed on every deploy would wipe every leaderboard. seed_changed() reseeds only
the quizzes whose JSON actually changed.
"""
import json
import os

from app.db import connect, init_schema
from app.seed import seed_changed


def _doc(slug, prompt="هل الفجوة البحثية تُشتق من مراجعة الأدبيات؟"):
    return {
        "slug": slug,
        "title_ar": "محطة اختبار",
        "pdf_filename": "x.pdf",
        "fun_facts_ar": [],
        "questions": [
            {
                "type": "tf",
                "prompt_ar": prompt,
                "options_ar": ["صح", "خطأ"],
                "correct_index": 0,
                "concept": "research_gap",
                "explanation_ar": "الفجوة تُشتق من مراجعة الأدبيات.",
            }
        ],
    }


def _write(dirpath, slug, prompt=None):
    doc = _doc(slug) if prompt is None else _doc(slug, prompt)
    path = os.path.join(dirpath, f"{slug}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    return path


def _fresh():
    conn = connect(":memory:")
    init_schema(conn)
    return conn


def test_first_run_seeds_then_second_run_skips(tmp_path):
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")

    first = seed_changed(conn, d)
    assert first["seeded"] == ["alpha"]
    assert first["skipped"] == []

    second = seed_changed(conn, d)
    assert second["seeded"] == []
    assert second["skipped"] == ["alpha"]


def test_only_the_changed_quiz_is_reseeded(tmp_path):
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")
    _write(d, "beta")
    seed_changed(conn, d)

    _write(d, "beta", prompt="سؤال مختلف تمامًا عن السابق؟")
    result = seed_changed(conn, d)

    assert result["seeded"] == ["beta"]
    assert result["skipped"] == ["alpha"]


def test_unchanged_quiz_keeps_its_attempts(tmp_path):
    """The regression this whole feature exists to prevent."""
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")
    seed_changed(conn, d)

    quiz_id = conn.execute("SELECT id FROM quizzes WHERE slug='alpha'").fetchone()["id"]
    conn.execute(
        "INSERT INTO contestants (telegram_user_id, first_name, created_at) VALUES (?, ?, ?)",
        (7, "Vi", "2026-01-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO attempts (contestant_id, quiz_id, total_score) VALUES (?, ?, ?)",
        (7, quiz_id, 900),
    )
    conn.commit()

    seed_changed(conn, d)  # content unchanged

    assert conn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"] == 1


def test_changing_one_quiz_preserves_the_other_leaderboard(tmp_path):
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")
    _write(d, "beta")
    seed_changed(conn, d)

    conn.execute(
        "INSERT INTO contestants (telegram_user_id, first_name, created_at) VALUES (?, ?, ?)",
        (7, "Vi", "2026-01-01T00:00:00Z"),
    )
    for slug in ("alpha", "beta"):
        qid = conn.execute("SELECT id FROM quizzes WHERE slug=?", (slug,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO attempts (contestant_id, quiz_id, total_score) VALUES (?, ?, ?)",
            (7, qid, 500),
        )
    conn.commit()

    _write(d, "beta", prompt="محتوى جديد للمحطة الثانية؟")
    seed_changed(conn, d)

    alpha_id = conn.execute("SELECT id FROM quizzes WHERE slug='alpha'").fetchone()["id"]
    remaining = conn.execute(
        "SELECT COUNT(*) c FROM attempts WHERE quiz_id = ?", (alpha_id,)
    ).fetchone()["c"]
    assert remaining == 1, "editing beta must not touch alpha's leaderboard"
    assert conn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"] == 1


def test_force_reseeds_everything(tmp_path):
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")
    seed_changed(conn, d)

    result = seed_changed(conn, d, force=True)
    assert result["seeded"] == ["alpha"]
    assert result["skipped"] == []


def test_adopts_an_existing_quiz_that_has_no_stored_hash(tmp_path):
    """The production incident of 2026-07-29.

    A database seeded before content hashing existed has rows but no
    `content_sha:<slug>` in `meta`. Treating "no hash" as "changed" reseeds the
    quiz and DELETES every attempt — which is exactly what happened on the first
    real deploy. When a quiz already exists and its provenance is unknown, the
    safe action is to adopt the current content (record the hash, change nothing)
    rather than destroy user data we cannot get back.
    """
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")
    seed_changed(conn, d)

    quiz_id = conn.execute("SELECT id FROM quizzes WHERE slug='alpha'").fetchone()["id"]
    conn.execute(
        "INSERT INTO contestants (telegram_user_id, first_name, created_at) VALUES (?, ?, ?)",
        (7, "Vi", "2026-01-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO attempts (contestant_id, quiz_id, total_score) VALUES (?, ?, ?)",
        (7, quiz_id, 459),
    )
    # Simulate a pre-hashing database: rows present, provenance unknown.
    conn.execute("DELETE FROM meta WHERE key = 'content_sha:alpha'")
    conn.commit()

    result = seed_changed(conn, d)

    assert result["adopted"] == ["alpha"]
    assert result["seeded"] == []
    assert conn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"] == 1, \
        "adopting must not delete attempts"
    # The hash is now recorded, so subsequent runs skip normally.
    assert seed_changed(conn, d)["skipped"] == ["alpha"]


def test_force_still_reseeds_an_adopted_quiz(tmp_path):
    conn = _fresh()
    d = str(tmp_path)
    _write(d, "alpha")
    seed_changed(conn, d)
    conn.execute("DELETE FROM meta WHERE key = 'content_sha:alpha'")
    conn.commit()

    assert seed_changed(conn, d, force=True)["seeded"] == ["alpha"]
