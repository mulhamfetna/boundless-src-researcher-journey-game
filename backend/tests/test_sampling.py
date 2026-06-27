import random
from collections import Counter
from app.sampling import sample_questions


def _bank(counts):
    # counts: {concept: n} -> list of question dicts with unique ids
    qs, i = [], 0
    for concept, n in counts.items():
        for _ in range(n):
            qs.append({"id": i, "concept": concept})
            i += 1
    return qs


def test_returns_exactly_size_when_bank_larger():
    bank = _bank({"a": 10, "b": 10, "c": 10})
    out = sample_questions(bank, 10, random.Random(1))
    assert len(out) == 10


def test_returns_all_when_bank_not_larger_than_size():
    bank = _bank({"a": 3, "b": 2})
    out = sample_questions(bank, 10, random.Random(1))
    assert len(out) == 5
    assert {q["id"] for q in out} == {q["id"] for q in bank}


def test_balances_across_concepts():
    # 3 concepts, ample supply, size 9 -> 3 per concept
    bank = _bank({"a": 10, "b": 10, "c": 10})
    out = sample_questions(bank, 9, random.Random(2))
    counts = Counter(q["concept"] for q in out)
    assert counts == {"a": 3, "b": 3, "c": 3}


def test_overflows_into_remaining_concepts_when_one_is_small():
    # concept 'a' has only 1; size 5 across a,b,c -> a contributes 1, rest fill from b,c
    bank = _bank({"a": 1, "b": 10, "c": 10})
    out = sample_questions(bank, 5, random.Random(3))
    assert len(out) == 5
    assert Counter(q["concept"] for q in out)["a"] == 1


def test_single_concept_bank_returns_size():
    bank = _bank({"a": 20})
    out = sample_questions(bank, 10, random.Random(4))
    assert len(out) == 10
    assert all(q["concept"] == "a" for q in out)


def test_deterministic_for_fixed_seed():
    bank = _bank({"a": 10, "b": 10, "c": 10})
    a = sample_questions(bank, 10, random.Random(99))
    b = sample_questions(bank, 10, random.Random(99))
    assert [q["id"] for q in a] == [q["id"] for q in b]


def test_does_not_mutate_input():
    bank = _bank({"a": 5, "b": 5})
    before = [q["id"] for q in bank]
    sample_questions(bank, 4, random.Random(5))
    assert [q["id"] for q in bank] == before
