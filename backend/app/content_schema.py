class SchemaError(Exception):
    pass


VALID_TYPES = {"mcq", "tf", "image"}


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def validate_quiz(doc: dict) -> None:
    for key in ("slug", "title_ar", "pdf_filename", "questions"):
        _require(key in doc and doc[key], f"missing field: {key}")
    _require(isinstance(doc["questions"], list) and doc["questions"], "questions must be a non-empty list")

    for i, q in enumerate(doc["questions"]):
        where = f"question[{i}]"
        _require(q.get("type") in VALID_TYPES, f"{where}: bad type {q.get('type')!r}")
        _require(bool(q.get("prompt_ar")), f"{where}: empty prompt_ar")

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
        if "asset" in q:
            a = q["asset"]
            _require(bool(a.get("file")), f"{where}: asset.file required")
            _require(bool(a.get("source_url")), f"{where}: asset.source_url required")
