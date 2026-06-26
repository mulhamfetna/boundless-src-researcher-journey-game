# Phase 2B — Remaining Quizzes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the three remaining research-methodology PDFs as new playable quizzes, so the app covers all four sessions.

**Architecture:** Reuse the entire existing engine (question types, partial-credit scoring, badges, per-quiz + overall leaderboards, auto-DM) unchanged. Add a `seed_all` loader to seed every quiz file, switch the bot's `/leaderboard` to the overall board, and author three curated content files grounded in the real PDFs.

**Tech Stack:** Python 3.14, FastAPI, stdlib sqlite3, python-telegram-bot, pytest; content as JSON validated by `app.content_schema`.

## Global Constraints

- **No engine/mechanics changes.** Reuse existing scoring, auth, badges, schema, and the Mini App runner/report as-is.
- **Language:** all learner-facing text is **Arabic, RTL**.
- **Each PDF = one quiz** with a stable `slug`; content lives in `content/questions/<slug>.json`, assets in `content/assets/<slug>/`.
- **Per-quiz content:** ~10–13 questions, a mix of `mcq`/`tf`/`match`/`order`, with **≥1 match and ≥1 order each**, grounded in the real PDF text (no invented facts).
- **Image questions only with a genuine sourced artifact.** Retry web sourcing; where blocked, the question is text-based or dropped. **Never fabricate a `source_url`.**
- **Content shapes** (must pass `app.content_schema.validate_quiz`):
  - mcq/tf/image: `{"type","prompt_ar","base_points","explanation_ar","source_page","options_ar":[...],"correct_index":n}` (+`asset` for image; tf has exactly 2 options).
  - match: `{...,"left_ar":[...],"right_ar":[...],"correct_pairs":[[li,ri],...]}` (each left index used at most once; indices in range).
  - order: `{...,"items_ar":[...],"correct_sequence":[...]}` (a permutation of `range(len(items_ar))`).
- **Slugs & order:** `foundations` (2), `paper-types` (3), `paper-parts` (4). Existing `journals` stays 1.
- **Package root:** backend under `backend/app/`, imported `app.<module>`; tests run from `backend/` with `pytest`. **Commit after every task.**

## Slug → PDF map

| slug | PDF filename | covers |
|------|--------------|--------|
| `foundations` | `أسس البحث العلمي واختيار الفجوة البحثية.pdf` | research foundations; choosing the research gap |
| `paper-types` | `أنواع الأوراق البحثية العلمية.pdf` | types of scientific papers |
| `paper-parts` | `اجزاء الورقة البحثية.pdf` | parts of a research paper |

---

### Task 1: `seed_all` — seed every quiz file

**Files:**
- Modify: `backend/app/seed.py`
- Create: `backend/tests/test_seed_all.py`

**Interfaces:**
- Consumes: existing `seed_quiz(conn, doc)`, `seed_from_file(conn, path)`.
- Produces: `app.seed.seed_all(conn, dir="content/questions") -> list[str]` — seeds every `*.json` in `dir` (sorted), each via `seed_quiz`, and returns the list of slugs seeded (in sorted-path order). Idempotent (delegates to the idempotent `seed_quiz`).

- [ ] **Step 1: Write the failing test** `backend/tests/test_seed_all.py`

```python
import json
from app.db import connect, init_schema
from app.seed import seed_all
from app.models import get_quiz_by_slug, get_questions


def _write(dir, slug, n):
    doc = {
        "slug": slug, "title_ar": f"عنوان {slug}", "pdf_filename": f"{slug}.pdf",
        "questions": [
            {"type": "mcq", "prompt_ar": f"س{i}", "options_ar": ["أ", "ب"], "correct_index": 0}
            for i in range(n)
        ],
    }
    (dir / f"{slug}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def test_seed_all_loads_every_file(tmp_path):
    qdir = tmp_path / "questions"
    qdir.mkdir()
    _write(qdir, "alpha", 2)
    _write(qdir, "beta", 3)
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    slugs = seed_all(conn, str(qdir))
    assert sorted(slugs) == ["alpha", "beta"]
    assert len(get_questions(conn, get_quiz_by_slug(conn, "beta")["id"])) == 3


def test_seed_all_idempotent(tmp_path):
    qdir = tmp_path / "questions"
    qdir.mkdir()
    _write(qdir, "alpha", 2)
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    seed_all(conn, str(qdir))
    seed_all(conn, str(qdir))
    assert len(get_questions(conn, get_quiz_by_slug(conn, "alpha")["id"])) == 2
```

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_seed_all.py -v`
Expected: FAIL — `ImportError: cannot import name 'seed_all'`.

- [ ] **Step 3: Append to `backend/app/seed.py`**

```python
import glob
import os


def seed_all(conn: sqlite3.Connection, dir: str = "content/questions") -> list[str]:
    slugs = []
    for path in sorted(glob.glob(os.path.join(dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        seed_quiz(conn, doc)
        slugs.append(doc["slug"])
    return slugs
```

(`json` and `sqlite3` are already imported at the top of `seed.py`; add the `glob` and `os` imports near the top with the others.)

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_seed_all.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/seed.py backend/tests/test_seed_all.py
git commit -m "feat: seed_all loads every quiz file"
```

---

### Task 2: Bot `/leaderboard` → overall board

**Files:**
- Modify: `backend/app/bot.py`
- Create: `backend/tests/test_bot_overall.py`

**Interfaces:**
- Consumes: `app.models.leaderboard_overall(conn, limit=20)` (columns `first_name`, `total_score`).
- Produces: `app.bot.overall_leaderboard_text(conn) -> str` — Arabic text of the overall board; an empty-state message when there are no finished attempts. `leaderboard_cmd` now replies with this instead of the per-`journals` board. The existing `leaderboard_text(conn, slug)` stays (unused by the command but kept for any per-quiz use).

- [ ] **Step 1: Write the failing test** `backend/tests/test_bot_overall.py`

```python
from app.bot import overall_leaderboard_text
from app.models import upsert_contestant, create_attempt, finish_attempt


def test_overall_text_lists_summed_scores(seeded):
    conn, quiz_id = seeded
    uid = upsert_contestant(conn, {"id": 9, "first_name": "Hala"})
    aid = create_attempt(conn, uid, quiz_id, "async", "2026-06-26T10:00:00")
    finish_attempt(conn, aid, 300, 1.0, 5000, "2026-06-26T10:00:05")
    text = overall_leaderboard_text(conn)
    assert "Hala" in text
    assert "300" in text


def test_overall_text_empty_state(seeded):
    conn, quiz_id = seeded
    text = overall_leaderboard_text(conn)
    assert isinstance(text, str) and text  # non-empty message, no crash
```

(Uses the existing `seeded` fixture from `backend/tests/conftest.py`.)

- [ ] **Step 2: Run it, expect failure**

Run: `cd backend && pytest tests/test_bot_overall.py -v`
Expected: FAIL — `ImportError: cannot import name 'overall_leaderboard_text'`.

- [ ] **Step 3: Edit `backend/app/bot.py`**

Change the models import line:
```python
from app.models import get_quiz_by_slug, leaderboard
```
to:
```python
from app.models import get_quiz_by_slug, leaderboard, leaderboard_overall
```

Add the new helper after `leaderboard_text`:
```python
def overall_leaderboard_text(conn) -> str:
    rows = leaderboard_overall(conn)
    if not rows:
        return "لا توجد نتائج بعد. كن أول المتسابقين! 🎮"
    lines = ["🏆 لوحة الصدارة الإجمالية"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['first_name']} — {r['total_score']}")
    return "\n".join(lines)
```

Change `leaderboard_cmd` to use it:
```python
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        await update.message.reply_text(overall_leaderboard_text(conn))
    finally:
        conn.close()
```

- [ ] **Step 4: Run it, expect pass**

Run: `cd backend && pytest tests/test_bot_overall.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/bot.py backend/tests/test_bot_overall.py
git commit -m "feat: bot /leaderboard shows overall board"
```

---

### Task 3: Content — `foundations` quiz

**Files:**
- Create: `content/questions/foundations.json`, assets under `content/assets/foundations/` (only if a real artifact is sourced)

**Interfaces:**
- Produces a schema-valid quiz: slug `foundations`, `display_order` 2, ~10–13 questions, ≥1 match + ≥1 order, grounded in `أسس البحث العلمي واختيار الفجوة البحثية.pdf`.

- [ ] **Step 1: Extract the source text**

Run:
```bash
python3 scripts/extract.py "أسس البحث العلمي واختيار الفجوة البحثية.pdf" content/raw/foundations.txt
```
Expected: `content/raw/foundations.txt` exists and is non-empty.

- [ ] **Step 2: Read `content/raw/foundations.txt`** and list ~10–13 real teaching points (e.g. what makes a research problem, identifying a research gap, literature-review role, research questions vs objectives, types of research). Note the page for each.

- [ ] **Step 3: (Optional) source a real artifact.** Verify network: `python3 -c "import urllib.request; urllib.request.urlopen('https://scholar.google.com', timeout=10); print('ok')"`. If reachable and a genuine relevant public screenshot exists (e.g. a real "research gap" diagram or a database search), download it into `content/assets/foundations/` and record its real `source_url`. If blocked, skip image questions for this quiz — author text-based questions only. Do NOT fabricate a source.

- [ ] **Step 4: Author `content/questions/foundations.json`** — slug `foundations`, `title_ar` (e.g. `أسس البحث العلمي واختيار الفجوة البحثية`), `pdf_filename` exactly `أسس البحث العلمي واختيار الفجوة البحثية.pdf`, `display_order` 2, and a `questions` array of ~10–13 items grounded in Step 2, with **≥1 match and ≥1 order**. Example skeleton (replace with real curated content):

```json
{
  "slug": "foundations",
  "title_ar": "أسس البحث العلمي واختيار الفجوة البحثية",
  "pdf_filename": "أسس البحث العلمي واختيار الفجوة البحثية.pdf",
  "display_order": 2,
  "questions": [
    {
      "type": "order",
      "prompt_ar": "رتّب خطوات تحديد الفجوة البحثية بالترتيب المنطقي.",
      "base_points": 120,
      "explanation_ar": "نبدأ بمراجعة الأدبيات ثم رصد ما لم يُبحث ثم صياغة سؤال البحث.",
      "source_page": 4,
      "items_ar": ["مراجعة الأدبيات الحالية", "رصد ما لم تتم دراسته", "صياغة سؤال البحث"],
      "correct_sequence": [0, 1, 2]
    },
    {
      "type": "match",
      "prompt_ar": "طابِق كل مصطلح مع تعريفه.",
      "base_points": 120,
      "explanation_ar": "الفجوة البحثية = نقص معرفي لم تتناوله الدراسات السابقة.",
      "source_page": 5,
      "left_ar": ["الفجوة البحثية", "سؤال البحث"],
      "right_ar": ["نقص معرفي غير مدروس", "صياغة استفهامية لما نريد الإجابة عنه"],
      "correct_pairs": [[0, 0], [1, 1]]
    },
    {
      "type": "mcq",
      "prompt_ar": "ما الهدف الأساسي من مراجعة الأدبيات قبل البحث؟",
      "base_points": 100,
      "explanation_ar": "تحديد ما أُنجز وما تبقّى من فجوات.",
      "source_page": 3,
      "options_ar": ["زيادة عدد المراجع", "تحديد الفجوة البحثية", "إطالة البحث", "تقليل التكلفة"],
      "correct_index": 1
    }
  ]
}
```

- [ ] **Step 5: Validate**

Run:
```bash
cd backend && python3 -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/foundations.json',encoding='utf-8'))); print('valid')"
```
Expected: `valid`. Confirm ≥10 questions with ≥1 match and ≥1 order.

- [ ] **Step 6: Commit**

```bash
git add content/questions/foundations.json content/assets/foundations/ 2>/dev/null; git add content/questions/foundations.json
git commit -m "feat: foundations quiz content"
```

---

### Task 4: Content — `paper-types` quiz

**Files:**
- Create: `content/questions/paper-types.json`, assets under `content/assets/paper-types/` (only if a real artifact is sourced)

**Interfaces:**
- Produces a schema-valid quiz: slug `paper-types`, `display_order` 3, ~10–13 questions, ≥1 match + ≥1 order, grounded in `أنواع الأوراق البحثية العلمية.pdf`.

- [ ] **Step 1: Extract**

Run:
```bash
python3 scripts/extract.py "أنواع الأوراق البحثية العلمية.pdf" content/raw/paper-types.txt
```
Expected: non-empty file.

- [ ] **Step 2: Read `content/raw/paper-types.txt`** and list ~10–13 real teaching points (e.g. original research article, review article, systematic review, case study, short communication, conference paper — their definitions and differences). Note pages.

- [ ] **Step 3: (Optional) source a real artifact** as in Task 3 Step 3 (verify network; only a genuine public screenshot; else text-only; never fabricate a source). Put any asset in `content/assets/paper-types/`.

- [ ] **Step 4: Author `content/questions/paper-types.json`** — slug `paper-types`, `title_ar` `أنواع الأوراق البحثية العلمية`, `pdf_filename` exactly `أنواع الأوراق البحثية العلمية.pdf`, `display_order` 3, ~10–13 grounded questions with **≥1 match and ≥1 order**. A strong match question here: match each paper TYPE to its defining trait. A strong order question: order the typical length/depth of paper types. Example match item (replace with real curated content):

```json
{
  "type": "match",
  "prompt_ar": "طابِق نوع الورقة البحثية مع سِمتها المميِّزة.",
  "base_points": 120,
  "explanation_ar": "المقالة الأصلية تعرض بيانات جديدة؛ ورقة المراجعة تلخّص أبحاثاً سابقة.",
  "source_page": 6,
  "left_ar": ["مقالة بحثية أصلية", "ورقة مراجعة", "دراسة حالة"],
  "right_ar": ["بيانات وتجارب جديدة", "تلخيص وتحليل أبحاث سابقة", "تحليل معمّق لحالة واحدة"],
  "correct_pairs": [[0, 0], [1, 1], [2, 2]]
}
```

- [ ] **Step 5: Validate**

Run:
```bash
cd backend && python3 -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/paper-types.json',encoding='utf-8'))); print('valid')"
```
Expected: `valid`; ≥10 questions, ≥1 match, ≥1 order.

- [ ] **Step 6: Commit**

```bash
git add content/questions/paper-types.json content/assets/paper-types/ 2>/dev/null; git add content/questions/paper-types.json
git commit -m "feat: paper-types quiz content"
```

---

### Task 5: Content — `paper-parts` quiz

**Files:**
- Create: `content/questions/paper-parts.json`, assets under `content/assets/paper-parts/` (only if a real artifact is sourced)

**Interfaces:**
- Produces a schema-valid quiz: slug `paper-parts`, `display_order` 4, ~10–13 questions, ≥1 match + ≥1 order, grounded in `اجزاء الورقة البحثية.pdf`.

- [ ] **Step 1: Extract**

Run:
```bash
python3 scripts/extract.py "اجزاء الورقة البحثية.pdf" content/raw/paper-parts.txt
```
Expected: non-empty file.

- [ ] **Step 2: Read `content/raw/paper-parts.txt`** and list ~10–13 real teaching points (the IMRaD parts: Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References — purpose of each). Note pages.

- [ ] **Step 3: (Optional) source a real artifact** as before (network check; genuine public screenshot only; else text-only; never fabricate). Put any asset in `content/assets/paper-parts/`.

- [ ] **Step 4: Author `content/questions/paper-parts.json`** — slug `paper-parts`, `title_ar` `اجزاء الورقة البحثية`, `pdf_filename` exactly `اجزاء الورقة البحثية.pdf`, `display_order` 4, ~10–13 grounded questions with **≥1 match and ≥1 order**. The natural order question: order the IMRaD sections as they appear in a paper. Example order item (replace/extend with real curated content):

```json
{
  "type": "order",
  "prompt_ar": "رتّب أجزاء الورقة البحثية بالترتيب الذي تظهر به.",
  "base_points": 120,
  "explanation_ar": "الترتيب القياسي IMRaD: المقدمة ثم المنهجية ثم النتائج ثم المناقشة.",
  "source_page": 2,
  "items_ar": ["المقدمة", "المنهجية", "النتائج", "المناقشة"],
  "correct_sequence": [0, 1, 2, 3]
}
```

- [ ] **Step 5: Validate**

Run:
```bash
cd backend && python3 -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/paper-parts.json',encoding='utf-8'))); print('valid')"
```
Expected: `valid`; ≥10 questions, ≥1 match, ≥1 order.

- [ ] **Step 6: Commit**

```bash
git add content/questions/paper-parts.json content/assets/paper-parts/ 2>/dev/null; git add content/questions/paper-parts.json
git commit -m "feat: paper-parts quiz content"
```

---

### Task 6: Live deploy — seed all four quizzes + verify

**Files:** none (operational), uses the running compose stack.

- [ ] **Step 1: Rebuild images** (picks up `seed_all` + bot change)

Run: `docker compose build web bot`
Expected: builds succeed.

- [ ] **Step 2: Migrate (idempotent; no schema change expected)**

Run: `docker compose run --rm web python -m app.migrate`
Expected: `migrated: already current`.

- [ ] **Step 3: Seed all quizzes**

Run:
```bash
docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect; from app.seed import seed_all; c=connect('/data/quiz.db'); print('seeded', seed_all(c, '/srv/content/questions'))"
```
Expected: prints `seeded [...]` listing four slugs including `foundations`, `journals`, `paper-parts`, `paper-types`.

- [ ] **Step 4: Restart + verify**

Run:
```bash
docker compose up -d web bot cloudflared
curl -s https://src.mulhamfetna.com/api/quizzes | python3 -c "import sys,json; print('quizzes:', [q['slug'] for q in json.load(sys.stdin)])"
curl -s "https://src.mulhamfetna.com/api/leaderboard?scope=overall"
```
Expected: all four slugs listed; overall board returns JSON (possibly `[]` until played).

- [ ] **Step 5: End-to-end (manual, Telegram)**

- [ ] Home lists all four quizzes in order (journals, foundations, paper-types, paper-parts).
- [ ] Each new quiz is playable, including its match and order questions.
- [ ] Finishing any quiz shows the report + DM.
- [ ] Bot `/leaderboard` shows the **overall** board; the Mini App overall toggle ranks across quizzes.

- [ ] **Step 6: Commit** any docs touch-ups if needed (e.g. note `seed_all` in DEPLOY.md):

Add to `docs/DEPLOY.md` Step 5 a note: "To load all quizzes at once use `seed_all(c, '/srv/content/questions')` instead of `seed_from_file`." Then:
```bash
git add docs/DEPLOY.md
git commit -m "docs: mention seed_all for multi-quiz seeding"
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- All 3 PDFs as separate quizzes → Tasks 3, 4, 5. ✓
- ~10–13 Qs/quiz, ≥1 match + ≥1 order → stated in each content task + validated in Step 5. ✓
- Image only with genuine sourced artifact, text-only fallback, never fabricate → Step 3 of each content task. ✓
- `seed_all` multi-quiz loader → Task 1; used in deploy Task 6. ✓
- Bot `/leaderboard` → overall → Task 2. ✓
- Deploy + verify all four + overall → Task 6. ✓
- No engine/mechanics change → only `seed.py` (additive), `bot.py` (command target), and content; scoring/auth/badges/schema/runner untouched. ✓

**Placeholder scan:** No "TBD/handle errors" in code steps. The interactive content steps (read PDF, source artifact, author Arabic) are inherent to the "real source" requirement and bounded by `validate_quiz` + concrete JSON skeletons.

**Type consistency:** `seed_all(conn, dir) -> list[str]` used identically in Task 1 and Task 6. `overall_leaderboard_text(conn) -> str` defined in Task 2 and consumed by `leaderboard_cmd`. Content shapes match `validate_quiz` (verified against the schema: match uses `left_ar`/`right_ar`/`correct_pairs`; order uses `items_ar`/`correct_sequence`). Slugs/display_order consistent with the spec.

## Out of scope
- Phase 3 (live timed sessions), a combined final-boss quiz, and any mechanics/UI change.
