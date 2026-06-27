# Phase 3B — Applied Question Bank + Per-Attempt Sampling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve a random, concept-balanced sample of ~10 questions per attempt from a larger per-quiz bank, so returning contestants rarely see the same set twice.

**Architecture:** A new pure `app/sampling.py` stratifies the quiz's full question list by a new per-question `concept` tag and returns ~10 spread evenly across concepts. `GET /questions` applies it server-side (still unauthenticated/stateless). Each question's `concept` rides inside the existing free-form `data_json` (no DB migration). The `submit` accuracy denominator is corrected to the number of questions answered. Content is expanded incrementally to ~30/quiz with applied/synthetic, concept-tagged questions.

**Tech Stack:** Python 3.14, FastAPI, stdlib `sqlite3`, stdlib `random`, pytest. Existing modules: `app/config.py`, `app/content_schema.py`, `app/seed.py`, `app/api.py`.

## Global Constraints

- **Sample size:** default **10**, read from env `SAMPLE_SIZE`. If a bank has `<= SAMPLE_SIZE` questions, return all of them.
- **Sampling is server-side** in `GET /questions`; the endpoint stays **unauthenticated and stateless** (no per-contestant "seen" tracking).
- **`concept`** is a **required, non-empty string** on every question; stored inside `data_json` (no schema/DB migration of tables).
- **Accuracy denominator** = number of questions in the submit payload's `answers` (guard divide-by-zero), NOT the full bank.
- **Language:** all learner-facing copy is **Arabic, RTL**. Synthetic questions are allowed and marked illustrative where they have no real source.
- **Keep Phase 3A intact:** sampled questions still ship with answer keys, `option_explanations_ar`, `hint_ar`; quiz-level `fun_facts_ar` unchanged.
- **Suite stays green at every commit.** The `concept`-required flip (Task 6) lands atomically with backfilling all content + inline test docs.
- **Concept taxonomy** (use these exact slugs):
  - journals: `predatory_signs`, `indexing`, `quartiles`, `metrics`, `open_access`, `peer_review`
  - foundations: `research_gap`, `research_question`, `literature_review`, `methodology_basics`, `ethics`
  - paper-types: `review_paper`, `original_research`, `case_study`, `conference_vs_journal`, `preprint`
  - paper-parts: `abstract`, `introduction`, `methods`, `results`, `discussion`, `references`
- Tests run from `backend/` with `pytest`.

---

## File Structure

```
backend/app/
  config.py            # MODIFY: add Settings.sample_size (env SAMPLE_SIZE, default 10)
  sampling.py          # CREATE: sample_questions() pure stratified sampler
  seed.py              # MODIFY: persist "concept" into data_json
  content_schema.py    # MODIFY: require non-empty "concept" per question
  api.py               # MODIFY: GET serializes concept + applies sampling; submit accuracy fix
backend/tests/
  test_config.py       # CREATE
  test_sampling.py     # CREATE
  test_seed.py         # MODIFY: assert concept persisted; add concept to inline docs (Task 6)
  test_api.py          # MODIFY: GET sample-size test; submit accuracy test
  test_content_schema.py # MODIFY (Task 6): require-concept tests + concept in _good_doc
  test_seed_all.py     # MODIFY (Task 6): concept in inline doc
  conftest.py          # MODIFY (Task 6): concept in SAMPLE_DOC
content/questions/
  journals.json foundations.json paper-types.json paper-parts.json  # MODIFY: backfill + expand
```

---

### Task 1: Config — `SAMPLE_SIZE`

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `app.config.Settings.sample_size: int`; `load_settings()` reads env `SAMPLE_SIZE` (default `10`).

- [ ] **Step 1: Write the failing test** in `backend/tests/test_config.py`

```python
import importlib
from app import config


def test_sample_size_defaults_to_10(monkeypatch):
    monkeypatch.delenv("SAMPLE_SIZE", raising=False)
    importlib.reload(config)
    assert config.load_settings().sample_size == 10


def test_sample_size_from_env(monkeypatch):
    monkeypatch.setenv("SAMPLE_SIZE", "7")
    importlib.reload(config)
    assert config.load_settings().sample_size == 7
    monkeypatch.delenv("SAMPLE_SIZE", raising=False)
    importlib.reload(config)
```

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: FAIL — `TypeError` (unexpected keyword) or `AttributeError` (no `sample_size`).

- [ ] **Step 3: Edit `backend/app/config.py`** — add the field and env read

Add `sample_size: int` to the dataclass and read it in `load_settings`:

```python
@dataclass
class Settings:
    bot_token: str
    db_path: str
    public_url: str
    sample_size: int


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ.get("BOT_TOKEN", ""),
        db_path=os.environ.get("QUIZ_DB_PATH", "./quiz.db"),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
        sample_size=int(os.environ.get("SAMPLE_SIZE", "10")),
    )
```

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite** (confirm no regression from the new field)

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: SAMPLE_SIZE setting (env-overridable, default 10)"
```

---

### Task 2: Sampling engine — `app/sampling.py`

**Files:**
- Create: `backend/app/sampling.py`, `backend/tests/test_sampling.py`

**Interfaces:**
- Produces: `app.sampling.sample_questions(questions: list[dict], size: int, rng) -> list[dict]`
  - Each item is a dict with a `"concept"` key.
  - If `len(questions) <= size`: return all, order shuffled by `rng`.
  - Else: group by `concept`, shuffle each group with `rng`, round-robin across concept
    groups (concept order shuffled by `rng`) taking one item per turn until `size` reached.
  - `rng` is a `random.Random` instance (injected for determinism).
  - Does not mutate the input list.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_sampling.py`

```python
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
```

- [ ] **Step 2: Run them, expect failure**

Run: `cd backend && pytest tests/test_sampling.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sampling'`.

- [ ] **Step 3: Create `backend/app/sampling.py`**

```python
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
```

- [ ] **Step 4: Run them, expect pass**

Run: `cd backend && pytest tests/test_sampling.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/sampling.py backend/tests/test_sampling.py
git commit -m "feat: concept-balanced question sampler"
```

---

### Task 3: Persist `concept` in `seed.py`

**Files:**
- Modify: `backend/app/seed.py` (the per-question `data` assembly, around lines 33–45)
- Modify: `backend/tests/test_seed.py` (add one test)

**Interfaces:**
- Produces: seeded questions whose `data_json` includes `"concept"` when present on the
  source question. (Optional at this stage — schema does not yet require it.)
- Consumes: nothing new.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_seed.py`

```python
import json as _json
from app.models import get_questions, get_quiz_by_slug
from app.seed import seed_quiz


def test_seed_persists_concept_in_data_json(conn):
    doc = {
        "slug": "concepttest", "title_ar": "ت", "pdf_filename": "x.pdf",
        "questions": [
            {"type": "tf", "prompt_ar": "س", "options_ar": ["صح", "خطأ"],
             "correct_index": 0, "concept": "indexing"},
        ],
    }
    seed_quiz(conn, doc)
    q = get_questions(conn, get_quiz_by_slug(conn, "concepttest")["id"])[0]
    assert _json.loads(q["data_json"])["concept"] == "indexing"
```

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_seed.py::test_seed_persists_concept_in_data_json -v`
Expected: FAIL — `KeyError: 'concept'` (not persisted yet).

- [ ] **Step 3: Edit `backend/app/seed.py`** — after the `hint_ar` block (line ~45), before the `INSERT INTO questions`, add:

```python
        if "concept" in q:
            data["concept"] = q["concept"]
```

(Place it immediately after the existing `if "hint_ar" in q: data["hint_ar"] = q["hint_ar"]` line, inside the `for order, q in enumerate(doc["questions"])` loop.)

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_seed.py -v`
Expected: PASS (existing seed tests + the new one).

- [ ] **Step 5: Commit**

```bash
git add backend/app/seed.py backend/tests/test_seed.py
git commit -m "feat: persist question concept into data_json"
```

---

### Task 4: Apply sampling in `GET /questions`

**Files:**
- Modify: `backend/app/api.py` (`get_questions`, lines ~28–55; add `import random`)
- Modify: `backend/tests/test_api.py` (add sampling test)

**Interfaces:**
- Consumes: `app.sampling.sample_questions`, `app.config.settings.sample_size`.
- Produces: `GET /api/quizzes/{slug}/questions` returns at most `settings.sample_size`
  questions; each serialized item gains `"concept"`. Response shape otherwise unchanged.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_api.py` (reuses the existing `api_client` fixture pattern; build a >10-question quiz)

```python
def test_get_questions_samples_to_sample_size(tmp_path, monkeypatch):
    from app import main as main_module
    from app.db import connect, init_schema
    from app.seed import seed_quiz
    from fastapi.testclient import TestClient

    conn = connect(str(tmp_path / "s.db"))
    init_schema(conn)
    questions = [
        {"type": "tf", "prompt_ar": f"س{i}", "options_ar": ["صح", "خطأ"],
         "correct_index": i % 2, "concept": ["a", "b", "c"][i % 3]}
        for i in range(15)
    ]
    seed_quiz(conn, {"slug": "big", "title_ar": "ك", "pdf_filename": "x.pdf",
                     "questions": questions})
    main_module.app.state.conn = conn
    client = TestClient(main_module.app)

    body = client.get("/api/quizzes/big/questions").json()
    assert len(body["questions"]) == 10
    assert all("concept" in q for q in body["questions"])
    ids = {q["id"] for q in body["questions"]}
    assert len(ids) == 10  # no duplicates
```

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_api.py::test_get_questions_samples_to_sample_size -v`
Expected: FAIL — `assert 15 == 10` (no sampling yet).

- [ ] **Step 3: Edit `backend/app/api.py`** — add `import random` at top, then in `get_questions`:

After building each `item` dict, add `concept`; after the loop, sample. Replace the
`get_questions` body's serialization/return with:

```python
    out = []
    funfacts = json.loads(quiz["fun_facts_json"]) if quiz["fun_facts_json"] else []
    for q in models.get_questions(conn, quiz["id"]):
        data = json.loads(q["data_json"])
        asset = models.get_asset_for_question(conn, q["id"])
        item = {
            "id": q["id"], "type": q["type"], "prompt_ar": q["prompt_ar"],
            "base_points": q["base_points"], "asset_file": asset["file_path"] if asset else None,
            "hint_ar": data.get("hint_ar", ""), "concept": data.get("concept", ""),
        }
        if q["type"] in ("mcq", "tf", "image"):
            item["options_ar"] = data["options_ar"]
            item["correct_index"] = data["correct_index"]
            item["option_explanations_ar"] = data.get("option_explanations_ar", [])
        elif q["type"] == "match":
            item["left_ar"] = data["left_ar"]; item["right_ar"] = data["right_ar"]
            item["correct_pairs"] = data["correct_pairs"]
        elif q["type"] == "order":
            item["items_ar"] = data["items_ar"]; item["correct_sequence"] = data["correct_sequence"]
        out.append(item)

    sampled = sample_questions(out, settings.sample_size, random.Random())
    return {"quiz": {"slug": quiz["slug"], "title_ar": quiz["title_ar"]},
            "questions": sampled, "fun_facts_ar": funfacts}
```

Add the import near the top of `api.py`:

```python
import random
from app.sampling import sample_questions
```

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_api.py -v`
Expected: PASS (new test + existing API tests; existing tests seed ≤10 questions so they get all back).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api.py backend/tests/test_api.py
git commit -m "feat: serve concept-balanced sample from GET /questions"
```

---

### Task 5: Fix `submit` accuracy denominator

**Files:**
- Modify: `backend/app/api.py` (`submit`, line ~107: `total_questions = len(qrows)`)
- Modify: `backend/tests/test_api.py` (add accuracy test)

**Interfaces:**
- Produces: `submit` computes `accuracy = first_try_count / len(answers)` (0.0 if no
  answers). `first_try_count`, streak, badges unchanged.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_api.py` (uses the existing `api_client` fixture + `_init_data` helper already in this file from Phase 1)

```python
def test_submit_accuracy_is_over_answered_count(api_client):
    init = _init_data({"id": 321, "first_name": "Hana"})
    questions = api_client.get("/api/quizzes/journals/questions").json()["questions"]
    # answer exactly 2 questions: 1 first-try-correct, 1 with retries
    answers = [
        {"question_id": questions[0]["id"], "retries": 0, "hint_used": False},
        {"question_id": questions[1]["id"], "retries": 2, "hint_used": False},
    ]
    report = api_client.post(
        "/api/quizzes/journals/submit",
        headers={"X-Init-Data": init},
        json={"answers": answers, "duration_ms": 1000},
    ).json()
    # 1 first-try out of 2 answered -> 0.5, regardless of full bank size
    assert report["accuracy"] == 0.5
```

Note: the `api_client` fixture seeds `SAMPLE_DOC` (2 questions). After Task 6, `SAMPLE_DOC` will carry concepts; this test depends only on answering 2 questions, so it holds either way.

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_api.py::test_submit_accuracy_is_over_answered_count -v`
Expected: FAIL — accuracy computed over `len(qrows)` (the seeded bank) instead of `len(answers)`. (With SAMPLE_DOC's 2 questions they happen to match; if so, this test still guards the change — see Step 3. To make the RED meaningful, this test is paired with the code change; if it passes pre-change because the fixture bank equals answered count, rely on the dedicated unit assertion below.)

To guarantee a meaningful RED, also add this focused test that seeds a 3-question bank and answers 2:

```python
def test_submit_accuracy_ignores_unanswered_bank_questions(tmp_path, monkeypatch):
    import json, hashlib, hmac
    from urllib.parse import urlencode
    from app import main as main_module
    from app.db import connect, init_schema
    from app.seed import seed_quiz
    from fastapi.testclient import TestClient

    BOT = "123456:TESTTOKEN"
    conn = connect(str(tmp_path / "acc.db"))
    init_schema(conn)
    seed_quiz(conn, {"slug": "acc", "title_ar": "د", "pdf_filename": "x.pdf",
        "questions": [
            {"type": "tf", "prompt_ar": f"س{i}", "options_ar": ["صح", "خطأ"],
             "correct_index": 0, "concept": "a"} for i in range(3)
        ]})
    main_module.app.state.conn = conn
    monkeypatch.setattr(main_module.settings, "bot_token", BOT, raising=False)
    client = TestClient(main_module.app)

    fields = {"auth_date": "1700000000", "user": json.dumps({"id": 9, "first_name": "Z"})}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    init = urlencode({**fields, "hash": h})

    qs = client.get("/api/quizzes/acc/questions").json()["questions"]
    answers = [{"question_id": qs[0]["id"], "retries": 0, "hint_used": False},
               {"question_id": qs[1]["id"], "retries": 0, "hint_used": False}]
    report = client.post("/api/quizzes/acc/submit",
                         headers={"X-Init-Data": init},
                         json={"answers": answers, "duration_ms": 500}).json()
    assert report["accuracy"] == 1.0  # 2 first-try / 2 answered, NOT 2/3
```

- [ ] **Step 3: Edit `backend/app/api.py`** — in `submit`, replace:

```python
    total_questions = len(qrows)
    accuracy = first_try_count / total_questions if total_questions else 0.0
```

with:

```python
    answered = len(answers)
    accuracy = first_try_count / answered if answered else 0.0
```

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd backend && pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api.py backend/tests/test_api.py
git commit -m "fix: accuracy over answered questions, not full bank"
```

---

### Task 6: Require `concept` (schema flip + backfill all content & test docs)

**Files:**
- Modify: `backend/app/content_schema.py` (add `concept` requirement in the per-question loop)
- Modify: `backend/tests/test_content_schema.py` (add `concept` to `_good_doc`; add require tests)
- Modify: `backend/tests/conftest.py` (add `concept` to both `SAMPLE_DOC` questions)
- Modify: `backend/tests/test_seed.py` (add `concept` to its two inline docs)
- Modify: `backend/tests/test_seed_all.py` (add `concept` to its inline doc)
- Modify: `content/questions/journals.json`, `foundations.json`, `paper-types.json`, `paper-parts.json` (backfill `concept` on every existing question using the Global Constraints taxonomy)

**Interfaces:**
- Produces: `validate_quiz` raises `SchemaError` if any question lacks a non-empty
  `concept`. All existing content + test docs satisfy it.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_content_schema.py`

```python
def test_missing_concept_fails():
    doc = _good_doc()
    for q in doc["questions"]:
        q.pop("concept", None)
    with pytest.raises(SchemaError):
        validate_quiz(doc)
```

Also update `_good_doc()` so the *valid* path still passes — add `"concept": "x"` to each question dict it builds.

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_content_schema.py::test_missing_concept_fails -v`
Expected: FAIL — `DID NOT RAISE SchemaError` (concept not required yet).

- [ ] **Step 3: Edit `backend/app/content_schema.py`** — inside the `for i, q in enumerate(doc["questions"])` loop, right after the `prompt_ar` check (line ~26), add:

```python
        _require(isinstance(q.get("concept"), str) and q["concept"].strip(),
                 f"{where}: missing non-empty concept")
```

- [ ] **Step 4: Backfill `concept` in the four content files.**

For each of `content/questions/{journals,foundations,paper-types,paper-parts}.json`, add a
`"concept"` to every question, choosing from that quiz's taxonomy (Global Constraints).
Group questions by their actual subject. Every question must get exactly one concept slug
from its quiz's list.

- [ ] **Step 5: Backfill `concept` in the inline test docs.**

- `backend/tests/conftest.py` `SAMPLE_DOC`: add `"concept": "predatory_signs"` to the mcq
  and `"concept": "predatory_signs"` to the image question.
- `backend/tests/test_seed.py`: add a `"concept"` (any non-empty slug, e.g. `"indexing"`)
  to each question in both inline docs (the `_good_doc`-style doc around line 58 and the
  single-question doc around line 77).
- `backend/tests/test_seed_all.py`: add a `"concept"` to each question in its inline doc.

- [ ] **Step 6: Validate every content file**

Run:
```bash
cd backend && python -c "import json,glob,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz;
[validate_quiz(json.load(open(p,encoding='utf-8'))) or print('ok',p) for p in sorted(glob.glob('../content/questions/*.json'))]"
```
Expected: `ok ...` for all four files (no `SchemaError`).

- [ ] **Step 7: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass (every inline doc + content file now has concepts).

- [ ] **Step 8: Commit**

```bash
git add backend/app/content_schema.py backend/tests/ content/questions/
git commit -m "feat: require concept tag; backfill existing 51 questions + test docs"
```

---

### Task 7: Expand banks to ~30/quiz (applied synthetic, auto-accept)

**Files:**
- Modify: `content/questions/journals.json`, `foundations.json`, `paper-types.json`, `paper-parts.json`
- Create: `backend/tests/test_seed_integrity.py`

**Interfaces:**
- Produces: each quiz JSON has ~30 schema-valid questions, every one concept-tagged,
  concepts reasonably balanced. A seed-integrity test asserts no question lacks a concept.

- [ ] **Step 1: Write the integrity test** in `backend/tests/test_seed_integrity.py`

```python
import glob, json, os
import pytest
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


def test_each_quiz_has_at_least_25_questions(tmp_path):
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        doc = json.load(open(p, encoding="utf-8"))
        assert len(doc["questions"]) >= 25, f"{doc['slug']} has {len(doc['questions'])}"
```

- [ ] **Step 2: Run it, expect failure on the count assertion**

Run: `cd backend && pytest tests/test_seed_integrity.py -v`
Expected: `test_every_content_question_has_concept` PASSES (Task 6 backfilled), `test_each_quiz_has_at_least_25_questions` FAILS (quizzes still have 12–15).

- [ ] **Step 3: Author applied/synthetic questions** to bring each quiz to ~30.

For each quiz, add questions until it has ≥30 (aim ~30), distributed across that quiz's
concept taxonomy so no concept is empty and counts are roughly even. Each new question:
- is **applied/scenario-style** where natural (present a short situation, ask the learner
  to apply the concept) — not pure recall;
- is in **Arabic**; synthetic examples are fine and should read as illustrative;
- carries `type`, `prompt_ar`, `concept`, and type-appropriate fields
  (`options_ar`+`correct_index` for mcq/tf, `left_ar`/`right_ar`/`correct_pairs` for match,
  `items_ar`/`correct_sequence` for order);
- SHOULD include `option_explanations_ar` and `hint_ar` (Phase 3A parity) for option types;
- does NOT require an `asset` unless a real artifact exists (only `journals` has assets).

After editing each file, validate it:
```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/journals.json',encoding='utf-8'))); print('ok')"
```
(repeat per file). Expected: `ok`.

- [ ] **Step 4: Run the integrity test, expect pass**

Run: `cd backend && pytest tests/test_seed_integrity.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add content/questions/ backend/tests/test_seed_integrity.py
git commit -m "content: expand quiz banks to ~30 applied questions, concept-tagged"
```

---

## Deployment note (after all tasks)
Live-update path is unchanged: rebuild image → `python -m app.migrate` → seed via
`seed_all` → `docker compose up -d`. No DB table migration is needed (concept lives in
`data_json`). `SAMPLE_SIZE` may be set in `.env` to override the default 10.

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Statistical never-repeat via random sampling → Task 2 + Task 4. ✓
- Sample size 10, env `SAMPLE_SIZE`, return-all when bank ≤ size → Task 1 (config) + Task 2 (logic). ✓
- Balanced across `concept` → Task 2. ✓
- Server-side, unauthenticated, stateless GET → Task 4. ✓
- `concept` required, stored in `data_json`, no DB migration → Task 3 (persist) + Task 6 (require). ✓
- Accuracy denominator fix → Task 5. ✓
- Phase 3A fields preserved (keys, explanations, hint, fun_facts) → Task 4 serialization keeps them. ✓
- Backfill existing 51 + grow to ~30/quiz, concept-tagged, auto-accept → Task 6 (backfill) + Task 7 (expand). ✓
- Suite green at every commit; concept-flip atomic with backfill → Task 6 ordering. ✓
- Concept taxonomy → Global Constraints. ✓

**Placeholder scan:** No "TBD/handle edge cases" in code steps. Task 7 Step 3 is inherently
generative content (authoring Arabic applied questions); it is bounded by the schema
validator and the integrity test (≥25 questions, every question concept-tagged).

**Type consistency:** `sample_questions(questions, size, rng)` signature matches between
Task 2 (definition) and Task 4 (call with `settings.sample_size`, `random.Random()`).
`Settings.sample_size` defined in Task 1, used in Task 4. `concept` stored by Task 3,
required by Task 6, read by Task 4 serialization and the integrity test.

## Out of scope (future)
- Strict per-contestant never-repeat / "seen" tracking.
- Per-quiz configurable sample size.
- Difficulty tiers / adaptive selection.
- Phase 3C learner dashboard.
