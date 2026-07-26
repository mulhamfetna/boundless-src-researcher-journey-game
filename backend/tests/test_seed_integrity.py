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


# Every station is now APPLICATION-FIRST: a small bank of rich hands-on tasks
# (see the 2026-07-26 specs). Bank <= sample size, so all tasks are played each
# attempt. We only require a playable minimum, not the old >=25 recall bank.
def test_each_quiz_has_enough_questions(tmp_path):
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        doc = json.load(open(p, encoding="utf-8"))
        n = len(doc["questions"])
        assert n >= 5, f"{doc['slug']} has only {n} tasks (< 5)"
