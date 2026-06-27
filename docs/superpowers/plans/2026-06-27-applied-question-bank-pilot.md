# Applied Question Bank (pilot) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-paper, hands-on applied questions — starting with an ~8–10 question pilot on `paper-parts` — by giving questions an optional `passage` (real excerpt) + `source_url`, plumbing them end-to-end, and sourcing real papers from DOAJ.

**Architecture:** Additive, frontend+backend, no DB migration. Questions gain optional `passage`/`source_url` stored in `data_json`; the runner renders a real-excerpt "paper" block; a `scripts/fetch_papers.py` DOAJ helper supports curation. Pilot content is authored into `paper-parts.json` and reseeded.

**Tech Stack:** FastAPI, stdlib `sqlite3`/`urllib`, pytest; dependency-free frontend + Vitest; `pdftoppm` for optional screenshots.

## Global Constraints

- **Additive schema:** questions may carry optional non-empty strings `passage` (real excerpt, LTR English) and `source_url`; stored in `data_json` (no DB migration). `concept` stays **required**.
- **Applied style:** identify/judge/choose from real material; `hint_ar` makes the learner act (count words, check rank, read the paragraph) — never definition recall.
- **Sourcing:** real open-access papers from **DOAJ**; every real-paper question records `source_url`. Short excerpts + citation (educational use).
- **Arabic, RTL** UI; the passage block renders **LTR**. Arcade theme; preserve element IDs/classes; `typeof`-guarded sprite calls.
- **Pilot only `paper-parts`** this plan; keep it ≥ 25 questions and every question `concept`-tagged.
- **`content/papers/` is a dev aid (gitignored** like `content/raw/`).
- **All existing tests stay green:** `./scripts/test.sh` (pytest 113 + vitest 32 + drag e2e).

---

## File Structure

```
backend/app/
  content_schema.py   # MODIFY: optional passage/source_url
  seed.py             # MODIFY: persist passage/source_url in data_json
  api.py              # MODIFY: get_questions serializes passage/source_url
  report.py           # MODIFY: build_report carries passage/source_url
backend/tests/
  test_content_schema.py  # MODIFY: passage/source_url cases
  test_seed.py            # MODIFY: round-trip
  test_api.py             # MODIFY: get_questions exposes them
scripts/
  fetch_papers.py     # CREATE: DOAJ fetch + parse_doaj()
  test_fetch_papers.py  # CREATE (pytest, no live call)
frontend/
  index.html          # MODIFY: #q-passage block in runner
  app.js              # MODIFY: render passage + source in runner & report
  styles.css          # MODIFY: .passage block
  tests/passage_ui.test.js  # CREATE
content/questions/paper-parts.json  # MODIFY: + applied questions
.gitignore            # MODIFY: content/papers/
```

---

### Task 1: Schema — optional `passage`/`source_url`

**Files:** Modify `backend/app/content_schema.py`, `backend/tests/test_content_schema.py`

**Interfaces:** `validate_quiz` accepts optional non-empty `passage`/`source_url` on `mcq`/`image`.

- [ ] **Step 1: Add failing tests** to `backend/tests/test_content_schema.py` (append)

```python
def test_passage_and_source_url_optional_ok():
    doc = _good_doc()
    doc["questions"][0]["passage"] = "We propose a method..."
    doc["questions"][0]["source_url"] = "https://doaj.org/article/abc"
    validate_quiz(doc)  # must not raise


def test_empty_passage_fails():
    doc = _good_doc()
    doc["questions"][0]["passage"] = "   "
    with pytest.raises(SchemaError):
        validate_quiz(doc)
```

- [ ] **Step 2: Run, expect fail** — `cd backend && pytest tests/test_content_schema.py -k "passage or source" -q` → `test_empty_passage_fails` fails (no validation yet).

- [ ] **Step 3: Edit `backend/app/content_schema.py`** — inside the per-question loop, after the
`hint_ar` check, add:

```python
        if "passage" in q:
            _require(isinstance(q["passage"], str) and q["passage"].strip(),
                     f"{where}: passage must be a non-empty string")
        if "source_url" in q:
            _require(isinstance(q["source_url"], str) and q["source_url"].strip(),
                     f"{where}: source_url must be a non-empty string")
```

- [ ] **Step 4: Run, expect pass** — `cd backend && pytest tests/test_content_schema.py -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/content_schema.py backend/tests/test_content_schema.py
git commit -m "feat(applied): optional passage/source_url in question schema"
```

---

### Task 2: Plumb `passage`/`source_url` (seed → api → report)

**Files:** Modify `backend/app/seed.py`, `backend/app/api.py`, `backend/app/report.py`, `backend/tests/test_seed.py`, `backend/tests/test_api.py`

**Interfaces:** seeded `data_json` includes `passage`/`source_url`; `GET /questions` items and report
items expose them.

- [ ] **Step 1: Add failing test** to `backend/tests/test_seed.py` (append)

```python
def test_seed_persists_passage_and_source(conn):
    doc = {
        "slug": "ap", "title_ar": "ت", "pdf_filename": "x.pdf",
        "questions": [{"type": "mcq", "prompt_ar": "س", "options_ar": ["أ", "ب"],
                       "correct_index": 0, "concept": "abstract",
                       "passage": "We study X.", "source_url": "https://doaj.org/a/1"}],
    }
    seed_quiz(conn, doc)
    q = get_questions(conn, get_quiz_by_slug(conn, "ap")["id"])[0]
    data = _json.loads(q["data_json"])
    assert data["passage"] == "We study X."
    assert data["source_url"] == "https://doaj.org/a/1"
```

- [ ] **Step 2: Run, expect fail** — `cd backend && pytest tests/test_seed.py::test_seed_persists_passage_and_source -q` → KeyError.

- [ ] **Step 3: Edit `backend/app/seed.py`** — after the `if "concept" in q: data["concept"] = q["concept"]` line, add:

```python
        if "passage" in q:
            data["passage"] = q["passage"]
        if "source_url" in q:
            data["source_url"] = q["source_url"]
```

- [ ] **Step 4: Edit `backend/app/api.py` `get_questions`** — in the per-question `item` dict, add
`passage`/`source_url` (alongside `concept`/`hint_ar`):

```python
        item = {
            "id": q["id"], "type": q["type"], "prompt_ar": q["prompt_ar"],
            "base_points": q["base_points"], "asset_file": asset["file_path"] if asset else None,
            "hint_ar": data.get("hint_ar", ""), "concept": data.get("concept", ""),
            "passage": data.get("passage", ""), "source_url": data.get("source_url", ""),
        }
```

- [ ] **Step 5: Edit `backend/app/report.py` `build_report`** — in the per-item dict, add:

```python
            "passage": data.get("passage", ""),
            "source_url": data.get("source_url", ""),
```

(append inside the `items.append({...})` dict).

- [ ] **Step 6: Add failing API test** to `backend/tests/test_api.py` (append)

```python
def test_get_questions_exposes_passage(tmp_path):
    conn = connect(str(tmp_path / "p.db"))
    init_schema(conn)
    seed_quiz(conn, {"slug": "ap", "title_ar": "ت", "pdf_filename": "x.pdf",
        "questions": [{"type": "mcq", "prompt_ar": "س", "options_ar": ["أ", "ب"],
                       "correct_index": 0, "concept": "abstract",
                       "passage": "Real excerpt.", "source_url": "https://doaj.org/a/1"}]})
    main_module.app.state.conn = conn
    c = TestClient(main_module.app)
    q = c.get("/api/quizzes/ap/questions").json()["questions"][0]
    assert q["passage"] == "Real excerpt."
    assert q["source_url"] == "https://doaj.org/a/1"
```

- [ ] **Step 7: Run, expect pass** — `cd backend && pytest tests/test_seed.py tests/test_api.py -q` → pass.

- [ ] **Step 8: Full backend suite** — `cd backend && pytest -q` → all pass.

- [ ] **Step 9: Commit**

```bash
git add backend/app/seed.py backend/app/api.py backend/app/report.py backend/tests/test_seed.py backend/tests/test_api.py
git commit -m "feat(applied): plumb passage/source_url through seed/api/report"
```

---

### Task 3: Runner renders the passage block (TDD)

**Files:** Modify `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`; Create `frontend/tests/passage_ui.test.js`

**Interfaces:** the runner shows a `#q-passage` block (LTR) + a `المصدر` link when the current
question has `passage`/`source_url`.

- [ ] **Step 1: Failing test** — `frontend/tests/passage_ui.test.js`

```javascript
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8").replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {} } };
  const questions = [{ id: 1, type: "mcq", prompt_ar: "ما هذا القسم؟", concept: "abstract",
    options_ar: ["مقدمة", "ملخص"], correct_index: 1, option_explanations_ar: ["", ""], hint_ar: "",
    passage: "We propose a novel method and report gains.", source_url: "https://doaj.org/a/1" }];
  const fetchMock = vi.fn((url) => Promise.resolve({ ok: true, json: async () =>
    String(url).includes("/questions") ? { quiz: { slug: "x", title_ar: "X" }, questions, fun_facts_ar: [] } : [] }));
  global.fetch = fetchMock;
  const factory = new Function("window", "document", "fetch", appSrc + "\n; return { startQuiz, show };");
  return factory(window, document, fetchMock);
}

describe("passage block", () => {
  it("renders the excerpt and a source link in the runner", async () => {
    const app = loadApp();
    await app.startQuiz("x");
    const p = document.getElementById("q-passage");
    expect(p.classList.contains("hidden")).toBe(false);
    expect(p.textContent).toContain("novel method");
    expect(p.querySelector("a").getAttribute("href")).toBe("https://doaj.org/a/1");
  });
});
```

- [ ] **Step 2: Run, expect fail** — `cd frontend && npm test -- passage` → `#q-passage` null / hidden.

- [ ] **Step 3: Add `#q-passage` to `frontend/index.html`** — in `#screen-runner`, after the
`#boss-banner` line and before `<h2 id="q-prompt">`:

```html
      <div id="q-passage" class="passage hidden"></div>
```

- [ ] **Step 4: Render it in `frontend/app.js` `renderQuestion`** — after the boss-banner block and
before reading `const q = ...` already exists; add right after `const q = state.questions[state.idx];`
(near the top of `renderQuestion`):

```javascript
  const passEl = document.getElementById("q-passage");
  if (passEl) {
    if (q.passage) {
      const src = q.source_url ? ` <a href="${q.source_url}" target="_blank" rel="noopener">المصدر</a>` : "";
      passEl.innerHTML = `<div class="passage-text" dir="ltr">${q.passage}</div><div class="passage-src">${src}</div>`;
      passEl.classList.remove("hidden");
    } else {
      passEl.classList.add("hidden");
      passEl.innerHTML = "";
    }
  }
```

- [ ] **Step 5: Show it in the report review** — in `renderReport`, inside the `report.items.forEach`
item HTML, add the passage before the prompt line:

```javascript
      (it.passage ? `<div class="passage-text" dir="ltr">${it.passage}</div>` : "") +
```
(insert as the first concatenated string in `div.innerHTML = ...`).

- [ ] **Step 6: Style the block** — append to `frontend/styles.css`:

```css
.passage { margin:8px 0 12px; }
.passage-text { background:var(--ink); border:3px solid var(--panel2); border-radius:4px; padding:12px;
  font-family:ui-monospace, Menlo, Consolas, monospace; font-size:.92rem; line-height:1.6; color:#dfe8ff;
  max-height:38vh; overflow:auto; text-align:left; }
.passage-src { text-align:left; margin-top:4px; }
.passage-src a { color:var(--gold); font-size:.8rem; }
```

- [ ] **Step 7: Run, expect pass** — `cd frontend && npm test -- passage` → passes.

- [ ] **Step 8: Full frontend suite + drag e2e** — `cd frontend && npm test && node tests/drag.e2e.mjs` → green.

- [ ] **Step 9: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css frontend/tests/passage_ui.test.js
git commit -m "feat(applied): runner + report render the real-paper passage block"
```

---

### Task 4: DOAJ fetch helper (TDD)

**Files:** Create `scripts/fetch_papers.py`, `scripts/test_fetch_papers.py`; Modify `.gitignore`

**Interfaces:** `parse_doaj(body: str) -> list[dict]` → candidate dicts `{title, journal, abstract,
source_url, authors}`; `fetch(query, page_size=10) -> list[dict]` (live; not unit-tested).

- [ ] **Step 1: Failing test** — `scripts/test_fetch_papers.py`

```python
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from fetch_papers import parse_doaj

SAMPLE = json.dumps({"results": [{
    "id": "abc123",
    "bibjson": {
        "title": "A Study of X",
        "abstract": "We propose a method and evaluate it.",
        "journal": {"title": "Journal of Open Research"},
        "author": [{"name": "A. Researcher"}],
    }}]})


def test_parse_doaj():
    cands = parse_doaj(SAMPLE)
    assert len(cands) == 1
    c = cands[0]
    assert c["title"] == "A Study of X"
    assert c["journal"] == "Journal of Open Research"
    assert "method" in c["abstract"]
    assert c["source_url"] == "https://doaj.org/article/abc123"
    assert c["authors"] == ["A. Researcher"]
```

- [ ] **Step 2: Run, expect fail** — `cd scripts && python3 -m pytest test_fetch_papers.py -q` → ImportError.

- [ ] **Step 3: Create `scripts/fetch_papers.py`**

```python
"""Fetch open-access paper candidates from DOAJ for curating applied questions.

Read-only research aid. Usage:
  python scripts/fetch_papers.py "research gap" 10 > content/papers/foundations.json
"""
import json
import sys
import urllib.parse
import urllib.request


def parse_doaj(body: str) -> list[dict]:
    data = json.loads(body)
    out = []
    for r in data.get("results", []):
        bib = r.get("bibjson", {})
        out.append({
            "title": bib.get("title", ""),
            "journal": (bib.get("journal") or {}).get("title", ""),
            "abstract": bib.get("abstract", ""),
            "authors": [a.get("name", "") for a in bib.get("author", []) if a.get("name")],
            "source_url": f"https://doaj.org/article/{r.get('id', '')}",
        })
    return out


def fetch(query: str, page_size: int = 10) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://doaj.org/api/search/articles/{q}?pageSize={page_size}"
    req = urllib.request.Request(url, headers={"User-Agent": "research-quiz/1.0"})
    body = urllib.request.urlopen(req, timeout=20).read().decode()
    return [c for c in parse_doaj(body) if c["abstract"]]


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "research methodology"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(json.dumps(fetch(query, n), ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Run, expect pass** — `cd scripts && python3 -m pytest test_fetch_papers.py -q` → 1 passed.

- [ ] **Step 5: Gitignore the candidates dir** — append to `.gitignore`:

```
content/papers/
```

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch_papers.py scripts/test_fetch_papers.py .gitignore
git commit -m "feat(applied): DOAJ paper-fetch helper for curation"
```

---

### Task 5: Author the `paper-parts` applied pilot (real DOAJ papers)

**Files:** Modify `content/questions/paper-parts.json` (+ optional `content/assets/paper-parts/` screenshots)

**Interfaces:** adds ~8–10 applied `mcq` questions with real `passage`/`source_url`.

- [ ] **Step 1: Fetch real candidates** (research aid)

Run:
```bash
cd /mnt/data/projects/Boundless/Gamified-sessions && mkdir -p content/papers
python3 scripts/fetch_papers.py "research methodology" 15 > content/papers/paper-parts.json
python3 scripts/fetch_papers.py "systematic review methods" 15 >> /dev/null 2>&1 || true
head -c 400 content/papers/paper-parts.json
```
Expected: a JSON array of real articles with abstracts + `source_url`.

- [ ] **Step 2: Author ~8–10 applied questions** into `content/questions/paper-parts.json`.

For each, pick a **real excerpt** from a fetched candidate's abstract (or a sentence/paragraph of it)
and build an applied `mcq`. Cover these shapes (using existing `paper-parts` concepts):
- "ما هذا القسم من الورقة؟" over a real abstract/intro/methods/results excerpt → `concept` =
  `abstract`/`introduction`/`methods`/`results`/`discussion`.
- "أيّ هذه المقاطع هو الملخص (Abstract)؟" — `passage` holds 3–4 short labelled excerpts → `concept: abstract`.
- "ما الخلل في هذه الفقرة؟" over an excerpt you lightly modify to introduce one flaw (e.g. results
  stated in the methods) → `concept: structure`; `explanation_ar` names the flaw.
Each question MUST include: `type:"mcq"`, `prompt_ar`, `options_ar`, `correct_index`,
`explanation_ar`, `concept` (a paper-parts concept), `hint_ar` (action-oriented), `passage` (real
excerpt), `source_url` (the candidate's DOAJ url), `base_points` (110–120). Keep excerpts short
(≤ ~80 words) and cited.

Example object to mirror:
```json
{
  "type": "mcq",
  "concept": "methods",
  "base_points": 115,
  "prompt_ar": "اقرأ المقطع التالي من ورقة منشورة. أيّ قسم من الورقة هو؟",
  "passage": "Participants were randomly assigned to two groups; data were collected over six weeks and analysed using a mixed-effects model.",
  "source_url": "https://doaj.org/article/REPLACE_WITH_REAL_ID",
  "options_ar": ["المقدمة", "المنهجية (Methods)", "النتائج", "المناقشة"],
  "correct_index": 1,
  "option_explanations_ar": ["المقدمة تؤطّر المشكلة لا الإجراءات.", "صحيح؛ وصف العيّنة وجمع البيانات والتحليل = قسم المنهجية.", "النتائج تعرض ما تم التوصّل إليه.", "المناقشة تفسّر النتائج."],
  "hint_ar": "ابحث عن وصف العيّنة وكيفية جمع البيانات وتحليلها — هذه بصمة قسمٍ بعينه.",
  "explanation_ar": "المقطع يصف تصميم الدراسة وجمع البيانات وتحليلها، وهي وظيفة قسم المنهجية."
}
```
(Replace `passage`/`source_url`/options with REAL curated content; do not ship the placeholder id.)

- [ ] **Step 3: Validate the file**

Run:
```bash
cd backend && python3 -c "import json,sys; sys.path.insert(0,'.'); from app.content_schema import validate_quiz; validate_quiz(json.load(open('../content/questions/paper-parts.json',encoding='utf-8'))); print('ok', len(json.load(open('../content/questions/paper-parts.json',encoding='utf-8'))['questions']))"
```
Expected: `ok N` with `N` ≥ 25 (existing + pilot) and no `SchemaError`.

- [ ] **Step 4: Confirm every applied question has a real source_url** (no placeholder)

Run:
```bash
cd /mnt/data/projects/Boundless/Gamified-sessions && ! grep -q "REPLACE_WITH_REAL_ID" content/questions/paper-parts.json && echo "no placeholders" || (echo "PLACEHOLDER LEFT" && exit 1)
```
Expected: `no placeholders`.

- [ ] **Step 5: Seed-integrity + suite**

Run: `cd backend && pytest tests/test_seed_integrity.py -q` → pass (every question concept-tagged; ≥25).

- [ ] **Step 6: Commit**

```bash
git add content/questions/paper-parts.json content/assets/paper-parts 2>/dev/null
git commit -m "content(applied): paper-parts pilot — applied questions on real DOAJ excerpts"
```

---

### Task 6: Full-suite gate + deploy + reseed

- [ ] **Step 1: Combined suite** — `./scripts/test.sh` → backend (113 + new); frontend vitest (32 + passage_ui); drag e2e.
- [ ] **Step 2: Deploy + reseed** (content change):

```bash
docker compose up -d --build
sleep 3
docker compose exec -T web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_all; c=connect('/data/quiz.db'); init_schema(c); print('seeded:', seed_all(c,'/srv/content/questions'))"
```
- [ ] **Step 3: Verify** a sampled `paper-parts` attempt can include a passage question:
`curl -s localhost:8000/api/quizzes/paper-parts/questions | python3 -c "import sys,json; qs=json.load(sys.stdin)['questions']; print('with_passage:', sum(1 for q in qs if q.get('passage')))"` (≥ 0; rerun a few times — sampling).

---

## Self-Review (completed by plan author)

**Spec coverage:** optional `passage`/`source_url` schema (§3) → Task 1; plumb seed/api/report (§5)
→ Task 2; runner+report render passage block LTR + source (§5) → Task 3; DOAJ sourcing pipeline
(§4) → Task 4; pilot `paper-parts` ~8–10 real-paper applied questions (§6) → Task 5; deploy+reseed
(§9) → Task 6. `content/papers/` gitignored → Task 4. ✓

**Placeholder scan:** The only template is Task 5's example question object, explicitly flagged
"replace with REAL"; Step 4 hard-fails the build if the placeholder id ships. No other
"TBD/handle later".

**Type consistency:** `passage`/`source_url` keys are consistent across schema (Task 1), `data_json`
(Task 2 seed), `get_questions` item + report item (Task 2), and the frontend `q.passage`/
`q.source_url`/`it.passage` reads (Task 3). `parse_doaj(body)->[{title,journal,abstract,authors,
source_url}]` (Task 4) matches its test.

## Out of scope (future)
- Scaling applied questions to journals/foundations/paper-types.
- PDF-screenshot rendering automation (manual `pdftoppm` per the spec when a question needs a real
  table/figure).
