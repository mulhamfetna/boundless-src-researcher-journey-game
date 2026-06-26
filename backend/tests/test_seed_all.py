import json
from app.db import connect, init_schema
from app.seed import seed_all
from app.models import get_quiz_by_slug, get_questions


def _write(dir, slug, n):
    doc = {
        "slug": slug, "title_ar": f"عنوان {slug}", "pdf_filename": f"{slug}.pdf",
        "questions": [
            {"type": "mcq", "prompt_ar": f"س{i}", "options_ar": ["أ", "ب"], "correct_index": 0}
            for i in range(n)
        ],
    }
    (dir / f"{slug}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def test_seed_all_loads_every_file(tmp_path):
    qdir = tmp_path / "questions"
    qdir.mkdir()
    _write(qdir, "alpha", 2)
    _write(qdir, "beta", 3)
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    slugs = seed_all(conn, str(qdir))
    assert sorted(slugs) == ["alpha", "beta"]
    assert len(get_questions(conn, get_quiz_by_slug(conn, "beta")["id"])) == 3


def test_seed_all_idempotent(tmp_path):
    qdir = tmp_path / "questions"
    qdir.mkdir()
    _write(qdir, "alpha", 2)
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    seed_all(conn, str(qdir))
    seed_all(conn, str(qdir))
    assert len(get_questions(conn, get_quiz_by_slug(conn, "alpha")["id"])) == 2
