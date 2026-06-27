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
                "concept": "indexing",
                "options_ar": ["أ", "ب", "ج", "د"],
                "correct_index": 1,
            },
            {
                "type": "image",
                "prompt_ar": "أيهما حقيقي؟",
                "concept": "predatory_signs",
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


def test_valid_match_passes():
    doc = _good_doc()
    doc["questions"].append({
        "type": "match", "prompt_ar": "طابق", "concept": "indexing",
        "left_ar": ["L0", "L1"], "right_ar": ["R0", "R1"],
        "correct_pairs": [[0, 1], [1, 0]],
    })
    validate_quiz(doc)


def test_valid_order_passes():
    doc = _good_doc()
    doc["questions"].append({
        "type": "order", "prompt_ar": "رتّب", "concept": "indexing",
        "items_ar": ["A", "B", "C"], "correct_sequence": [2, 0, 1],
    })
    validate_quiz(doc)


def test_match_pair_index_out_of_range_fails():
    doc = _good_doc()
    doc["questions"].append({
        "type": "match", "prompt_ar": "طابق",
        "left_ar": ["L0"], "right_ar": ["R0"], "correct_pairs": [[0, 5]],
    })
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_order_sequence_not_permutation_fails():
    doc = _good_doc()
    doc["questions"].append({
        "type": "order", "prompt_ar": "رتّب",
        "items_ar": ["A", "B"], "correct_sequence": [0, 0],
    })
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_option_explanations_length_must_match():
    doc = _good_doc()
    doc["questions"][0]["option_explanations_ar"] = ["a", "b"]  # 2 != 4 options
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_valid_explanations_hint_funfacts_pass():
    doc = _good_doc()
    doc["fun_facts_ar"] = ["معلومة"]
    q = doc["questions"][0]
    q["option_explanations_ar"] = ["خطأ", "خطأ", "صحيح", "خطأ"]
    q["hint_ar"] = "تلميح"
    validate_quiz(doc)


def test_funfacts_must_be_list_of_str():
    doc = _good_doc()
    doc["fun_facts_ar"] = "ليست قائمة"
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_missing_concept_fails():
    doc = _good_doc()
    for q in doc["questions"]:
        q.pop("concept", None)
    with pytest.raises(SchemaError):
        validate_quiz(doc)


def test_passage_and_source_url_optional_ok():
    doc = _good_doc()
    doc["questions"][0]["passage"] = "We propose a method..."
    doc["questions"][0]["source_url"] = "https://doaj.org/article/abc"
    validate_quiz(doc)


def test_empty_passage_fails():
    doc = _good_doc()
    doc["questions"][0]["passage"] = "   "
    with pytest.raises(SchemaError):
        validate_quiz(doc)
