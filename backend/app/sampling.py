from collections import defaultdict


def sample_questions(questions: list[dict], size: int, rng) -> list[dict]:
    """Return up to `size` questions, balanced across their `concept` tag.

    Deterministic for a fixed `rng` (a random.Random). Does not mutate input.
    """
    pool = list(questions)
    if len(pool) <= size:
        rng.shuffle(pool)
        return pool

    groups = defaultdict(list)
    for q in pool:
        groups[q["concept"]].append(q)

    concepts = list(groups.keys())
    rng.shuffle(concepts)
    for c in concepts:
        rng.shuffle(groups[c])

    selected = []
    # round-robin across concepts until we have `size`
    while len(selected) < size:
        progressed = False
        for c in concepts:
            if groups[c]:
                selected.append(groups[c].pop())
                progressed = True
                if len(selected) == size:
                    break
        if not progressed:
            break  # all groups exhausted (shouldn't happen: len(pool) > size)
    return selected
