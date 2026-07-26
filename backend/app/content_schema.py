class SchemaError(Exception):
    pass


VALID_TYPES = {"mcq", "tf", "image", "match", "order", "spot"}


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def validate_quiz(doc: dict) -> None:
    for key in ("slug", "title_ar", "pdf_filename", "questions"):
        _require(key in doc and doc[key], f"missing field: {key}")
    _require(isinstance(doc["questions"], list) and doc["questions"], "questions must be a non-empty list")

    if "fun_facts_ar" in doc:
        _require(isinstance(doc["fun_facts_ar"], list)
                 and all(isinstance(x, str) for x in doc["fun_facts_ar"]),
                 "fun_facts_ar must be a list of strings")

    for i, q in enumerate(doc["questions"]):
        where = f"question[{i}]"
        _require(q.get("type") in VALID_TYPES, f"{where}: bad type {q.get('type')!r}")
        _require(bool(q.get("prompt_ar")), f"{where}: empty prompt_ar")
        _require(isinstance(q.get("concept"), str) and q["concept"].strip(),
                 f"{where}: missing non-empty concept")

        if q["type"] in ("mcq", "tf", "image"):
            options = q.get("options_ar")
            _require(isinstance(options, list), f"{where}: options_ar must be a list")
            if q["type"] == "tf":
                _require(len(options) == 2, f"{where}: tf needs exactly 2 options")
            else:
                _require(len(options) >= 2, f"{where}: needs >= 2 options")
            ci = q.get("correct_index")
            _require(isinstance(ci, int) and 0 <= ci < len(options), f"{where}: correct_index out of range")
            if q["type"] == "image":
                _require("asset" in q, f"{where}: image question needs an asset")

        elif q["type"] == "match":
            left, right = q.get("left_ar"), q.get("right_ar")
            _require(isinstance(left, list) and left, f"{where}: left_ar must be non-empty list")
            _require(isinstance(right, list) and right, f"{where}: right_ar must be non-empty list")
            pairs = q.get("correct_pairs")
            _require(isinstance(pairs, list) and pairs, f"{where}: correct_pairs must be non-empty list")
            seen_left = set()
            for p in pairs:
                _require(isinstance(p, list) and len(p) == 2, f"{where}: each pair is [left_idx, right_idx]")
                li, ri = p
                _require(isinstance(li, int) and isinstance(ri, int), f"{where}: pair indices must be integers")
                _require(0 <= li < len(left), f"{where}: left index out of range")
                _require(0 <= ri < len(right), f"{where}: right index out of range")
                _require(li not in seen_left, f"{where}: left item {li} matched twice")
                seen_left.add(li)

        elif q["type"] == "order":
            items = q.get("items_ar")
            _require(isinstance(items, list) and len(items) >= 2, f"{where}: items_ar needs >= 2 items")
            seq = q.get("correct_sequence")
            _require(isinstance(seq, list) and all(isinstance(x, int) for x in seq) and sorted(seq) == list(range(len(items))),
                     f"{where}: correct_sequence must be a permutation of range(len(items_ar))")

        elif q["type"] == "spot":
            opts = q.get("options_ar")
            _require(isinstance(opts, list) and len(opts) >= 3, f"{where}: spot needs >= 3 chips")
            ci = q.get("correct_indices")
            _require(isinstance(ci, list) and ci, f"{where}: spot needs non-empty correct_indices")
            _require(all(isinstance(i, int) and 0 <= i < len(opts) for i in ci),
                     f"{where}: spot correct_indices out of range")
            _require(len(set(ci)) < len(opts), f"{where}: spot needs at least one non-correct chip")
            if "chip_explanations_ar" in q:
                _require(isinstance(q["chip_explanations_ar"], list)
                         and len(q["chip_explanations_ar"]) == len(opts),
                         f"{where}: chip_explanations_ar length must equal options_ar")

        if "option_explanations_ar" in q:
            _require(q["type"] in ("mcq", "tf", "image"),
                     f"{where}: option_explanations_ar only valid for option types")
            _require(isinstance(q["option_explanations_ar"], list)
                     and len(q["option_explanations_ar"]) == len(q.get("options_ar", [])),
                     f"{where}: option_explanations_ar length must equal options_ar")
        if "hint_ar" in q:
            _require(isinstance(q["hint_ar"], str), f"{where}: hint_ar must be a string")
        if "passage" in q:
            _require(isinstance(q["passage"], str) and q["passage"].strip(),
                     f"{where}: passage must be a non-empty string")
        if "source_url" in q:
            _require(isinstance(q["source_url"], str) and q["source_url"].strip(),
                     f"{where}: source_url must be a non-empty string")

        if "asset" in q:
            a = q["asset"]
            _require(bool(a.get("file")), f"{where}: asset.file required")
            _require(bool(a.get("source_url")), f"{where}: asset.source_url required")
