import glob
import json
import os

from app.db import connect, init_schema
from app.seed import seed_all
from app.models import get_questions, get_quiz_by_slug

CONTENT = os.path.join(os.path.dirname(__file__), "..", "..", "content", "questions")


def test_every_content_question_has_concept(tmp_path):
    conn = connect(str(tmp_path / "i.db"))
    init_schema(conn)
    slugs = seed_all(conn, CONTENT)
    assert slugs, "no content seeded"
    for slug in slugs:
        quiz = get_quiz_by_slug(conn, slug)
        rows = get_questions(conn, quiz["id"])
        for r in rows:
            data = json.loads(r["data_json"])
            assert data.get("concept", "").strip(), f"{slug} q{r['id']} missing concept"


# Application-first stations use fewer, richer hands-on tasks (see the journals
# pilot spec docs/superpowers/specs/2026-07-26-journals-application-pilot-design.md);
# their bank may be < the sample size, in which case every task is always played.
# Recall stations keep a large bank so per-attempt sampling stays varied.
APPLICATION_FIRST = {"journals"}


def test_each_quiz_has_enough_questions(tmp_path):
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        doc = json.load(open(p, encoding="utf-8"))
        n = len(doc["questions"])
        floor = 5 if doc["slug"] in APPLICATION_FIRST else 25
        assert n >= floor, f"{doc['slug']} has {n} (< {floor})"
