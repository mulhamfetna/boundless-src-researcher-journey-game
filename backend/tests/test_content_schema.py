import pytest
from app.content_schema import validate_quiz, SchemaError


def _good_doc():
    return {
        "slug": "journals",
        "title_ar": "تصنيف",
        "pdf_filename": "x.pdf",
        "questions": [
            {
                "type": "mcq",
                "prompt_ar": "سؤال",
                "options_ar": ["أ", "ب", "ج", "د"],
                "correct_index": 1,
            },
            {
                "type": "image",
                "prompt_ar": "أيهما حقيقي؟",
                "options_ar": ["اليسار", "اليمين"],
                "correct_index": 0,
                "asset": {"file": "assets/journals/a.png", "source_url": "https://e.x/a"},
            },
        ],
    }


def test_valid_doc_passes():
    validate_quiz(_good_doc())  # must not raise


def test_missing_slug_fails():
    doc = _good_doc()
    del doc["slug"]
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_correct_index_out_of_range_fails():
    doc = _good_doc()
    doc["questions"][0]["correct_index"] = 9
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_image_without_asset_fails():
    doc = _good_doc()
    del doc["questions"][1]["asset"]
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_tf_must_have_two_options():
    doc = _good_doc()
    doc["questions"].append(
        {"type": "tf", "prompt_ar": "صح؟", "options_ar": ["صح"], "correct_index": 0}
    )
    with pytest.raises(SchemaError):
        validate_quiz(doc)
