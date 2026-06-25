import json
import pytest
from app.db import connect, init_schema
from app.seed import seed_quiz


SAMPLE_DOC = {
    "slug": "journals",
    "title_ar": "تصنيف المجلات",
    "pdf_filename": "x.pdf",
    "questions": [
        {
            "type": "mcq",
            "prompt_ar": "سؤال 1",
            "base_points": 100,
            "explanation_ar": "شرح 1",
            "source_page": 3,
            "options_ar": ["أ", "ب", "ج", "د"],
            "correct_index": 2,
        },
        {
            "type": "image",
            "prompt_ar": "أيهما حقيقي؟",
            "base_points": 100,
            "explanation_ar": "شرح 2",
            "source_page": 5,
            "options_ar": ["اليسار", "اليمين"],
            "correct_index": 0,
            "asset": {
                "file": "assets/journals/compare.png",
                "source_url": "https://example.org/compare",
                "anonymized": True,
                "caption_ar": "بريدان",
            },
        },
    ],
}


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def seeded(conn):
    quiz_id = seed_quiz(conn, SAMPLE_DOC)
    return conn, quiz_id
