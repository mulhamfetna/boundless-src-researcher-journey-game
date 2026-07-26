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


# Stations with a deliberately small, fixed bank are exempt from the >=25
# recall-bank rule: the application-first journals pilot, and the ordered
# capstone journey (plays all its authored stages, never sampled). See the
# 2026-07-26 specs. Recall stations keep a large bank so sampling stays varied.
SMALL_BANK = {"journals": 5, "capstone": 8}


def test_each_quiz_has_enough_questions(tmp_path):
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        doc = json.load(open(p, encoding="utf-8"))
        n = len(doc["questions"])
        floor = SMALL_BANK.get(doc["slug"], 25)
        assert n >= floor, f"{doc['slug']} has {n} (< {floor})"
