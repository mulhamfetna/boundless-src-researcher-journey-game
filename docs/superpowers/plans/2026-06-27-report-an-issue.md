# Report-an-Issue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a learner submit an issue from the Mini App; store it with all Telegram `initData` metadata; let the owner read reports via an admin-gated `/reports` bot command (and the DB).

**Architecture:** A new `issue_reports` SQLite table; `POST /api/report` validates `initData` and stores text + every metadata field; a `/reports` bot command gated by `ADMIN_ID` formats recent reports; a small RTL report screen in the Mini App POSTs the text. One-way (no bot reply chat).

**Tech Stack:** FastAPI, stdlib `sqlite3`, python-telegram-bot, pytest; dependency-free frontend + Vitest.

## Global Constraints

- **Auth:** `POST /api/report` validates Telegram `initData` HMAC (401 on failure / no user), like `/me/dashboard`.
- **Metadata captured:** from `initData` `user` — `id, username, first_name, last_name, language_code, is_premium, allows_write_to_pm`; from `initData` top level — `auth_date, chat_type, chat_instance, query_id, start_param`; from the POST body — `platform, version`; plus `raw_json = json.dumps(parsed)`. Empty `text` → 400.
- **Admin gating:** `/reports` only for `effective_user.id == settings.admin_id`; `admin_id == 0` (env unset) denies everyone. Deny copy: `"هذا الأمر للمشرف فقط."`
- **One-way:** no bot replies to reports beyond the in-app confirmation.
- **Arabic, RTL**; arcade theme; preserve existing element IDs/classes; sprite calls `typeof`-guarded.
- **Schema change** → `db.init_schema` (`CREATE TABLE IF NOT EXISTS`, auto-created at startup) + idempotent `migrate.py` entry; deploy runs `python -m app.migrate`.
- **All existing tests stay green:** `./scripts/test.sh` (pytest 106 + vitest 31 + drag e2e).

---

## File Structure

```
backend/app/
  db.py        # MODIFY: issue_reports in SCHEMA
  migrate.py   # MODIFY: create issue_reports if absent
  models.py    # MODIFY: insert_issue_report, list_issue_reports
  api.py       # MODIFY: POST /api/report
  config.py    # MODIFY: Settings.admin_id (env ADMIN_ID)
  bot.py       # MODIFY: is_admin, format_reports, /reports command
backend/tests/
  test_reports.py   # CREATE (models + api + bot helpers)
frontend/
  index.html   # MODIFY: report button + screen-report
  app.js       # MODIFY: showReport() + wire button
  sprites.js   # MODIFY: add "bug" sprite
  tests/report_ui.test.js  # CREATE
.env.example   # MODIFY: ADMIN_ID
```

---

### Task 1: Schema + models (TDD)

**Files:** Modify `backend/app/db.py`, `backend/app/migrate.py`, `backend/app/models.py`; Create `backend/tests/test_reports.py`

**Interfaces:**
- Produces:
  - `models.insert_issue_report(conn, fields: dict) -> int` — inserts one row (`created_at = datetime('now')`); missing keys default to NULL/`""`.
  - `models.list_issue_reports(conn, limit=20) -> list[sqlite3.Row]` — newest first.

- [ ] **Step 1: Failing tests** — `backend/tests/test_reports.py`

```python
from app.models import insert_issue_report, list_issue_reports


def test_insert_and_list_issue_reports(conn):
    insert_issue_report(conn, {
        "telegram_user_id": 5, "username": "lina", "first_name": "Lina",
        "language_code": "ar", "is_premium": 1, "text": "زر لا يعمل",
        "platform": "ios", "raw_json": "{}",
    })
    insert_issue_report(conn, {"telegram_user_id": 6, "text": "ملاحظة"})
    rows = list_issue_reports(conn, limit=10)
    assert len(rows) == 2
    assert rows[0]["telegram_user_id"] == 6          # newest first
    assert rows[1]["username"] == "lina"
    assert rows[1]["text"] == "زر لا يعمل"
```

(The `conn` fixture from `tests/conftest.py` already runs `init_schema`.)

- [ ] **Step 2: Run, expect fail** — `cd backend && pytest tests/test_reports.py -q` → ImportError (no `insert_issue_report`) or `no such table: issue_reports`.

- [ ] **Step 3: Add the table to `backend/app/db.py`** — append to the `SCHEMA` string (before the closing `"""`):

```sql

CREATE TABLE IF NOT EXISTS issue_reports (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id   INTEGER,
    username           TEXT,
    first_name         TEXT,
    last_name          TEXT,
    language_code      TEXT,
    is_premium         INTEGER,
    allows_write_to_pm INTEGER,
    auth_date          TEXT,
    chat_type          TEXT,
    chat_instance      TEXT,
    query_id           TEXT,
    start_param        TEXT,
    platform           TEXT,
    app_version        TEXT,
    text               TEXT NOT NULL,
    raw_json           TEXT,
    created_at         TEXT NOT NULL
);
```

- [ ] **Step 4: Add the migration entry** to `backend/app/migrate.py` — inside `migrate()`, before `conn.commit()`:

```python
    reports_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='issue_reports'"
    ).fetchone()
    if not reports_exists:
        conn.executescript(
            """
            CREATE TABLE issue_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER, username TEXT, first_name TEXT, last_name TEXT,
                language_code TEXT, is_premium INTEGER, allows_write_to_pm INTEGER,
                auth_date TEXT, chat_type TEXT, chat_instance TEXT, query_id TEXT,
                start_param TEXT, platform TEXT, app_version TEXT,
                text TEXT NOT NULL, raw_json TEXT, created_at TEXT NOT NULL
            );
            """
        )
        changes.append("issue_reports.create")
```

- [ ] **Step 5: Add the model functions** to `backend/app/models.py` (append)

```python
_REPORT_COLS = [
    "telegram_user_id", "username", "first_name", "last_name", "language_code",
    "is_premium", "allows_write_to_pm", "auth_date", "chat_type", "chat_instance",
    "query_id", "start_param", "platform", "app_version", "text", "raw_json",
]


def insert_issue_report(conn, fields: dict) -> int:
    cols = _REPORT_COLS + ["created_at"]
    placeholders = ", ".join(["?"] * len(_REPORT_COLS)) + ", datetime('now')"
    values = [fields.get(c) for c in _REPORT_COLS]
    cur = conn.execute(
        f"INSERT INTO issue_reports ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cur.lastrowid


def list_issue_reports(conn, limit=20):
    return conn.execute(
        "SELECT * FROM issue_reports ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
```

- [ ] **Step 6: Run, expect pass** — `cd backend && pytest tests/test_reports.py -q` → 1 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db.py backend/app/migrate.py backend/app/models.py backend/tests/test_reports.py
git commit -m "feat(report): issue_reports table + insert/list models"
```

---

### Task 2: Config `ADMIN_ID` + bot `/reports` (TDD)

**Files:** Modify `backend/app/config.py`, `backend/app/bot.py`, `backend/tests/test_reports.py`; Modify `.env.example`

**Interfaces:**
- Produces: `config.Settings.admin_id: int`; `bot.is_admin(user_id, admin_id) -> bool`;
  `bot.format_reports(rows) -> str`; a `/reports` command handler registered in `build_application`.

- [ ] **Step 1: Add failing tests** to `backend/tests/test_reports.py` (append)

```python
from app.bot import is_admin, format_reports


def test_is_admin():
    assert is_admin(7, 7) is True
    assert is_admin(7, 8) is False
    assert is_admin(7, 0) is False   # admin_id unset -> deny all


def test_format_reports(conn):
    from app.models import insert_issue_report
    insert_issue_report(conn, {"telegram_user_id": 5, "username": "lina", "first_name": "Lina",
                               "language_code": "ar", "platform": "ios", "text": "زر معطّل"})
    from app.models import list_issue_reports
    txt = format_reports(list_issue_reports(conn))
    assert "زر معطّل" in txt
    assert "lina" in txt


def test_format_reports_empty():
    assert "لا" in format_reports([])  # some "no reports" message
```

- [ ] **Step 2: Run, expect fail** — `cd backend && pytest tests/test_reports.py -q` → ImportError (`is_admin`).

- [ ] **Step 3: Add `admin_id` to `backend/app/config.py`** — add the field + env read:

```python
@dataclass
class Settings:
    bot_token: str
    db_path: str
    public_url: str
    sample_size: int
    admin_id: int


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ.get("BOT_TOKEN", ""),
        db_path=os.environ.get("QUIZ_DB_PATH", "./quiz.db"),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
        sample_size=int(os.environ.get("SAMPLE_SIZE", "10")),
        admin_id=int(os.environ.get("ADMIN_ID", "0")),
    )
```

- [ ] **Step 4: Add the bot helpers + command** to `backend/app/bot.py`

Add imports at top: change the models import line to include the report fns:
```python
from app.models import get_quiz_by_slug, leaderboard, leaderboard_overall, list_issue_reports
```

Add the helpers + handler (before `build_application`):
```python
def is_admin(user_id: int, admin_id: int) -> bool:
    return bool(admin_id) and user_id == admin_id


def format_reports(rows) -> str:
    if not rows:
        return "لا توجد بلاغات بعد."
    lines = ["🐞 آخر البلاغات:"]
    for r in rows:
        who = r["first_name"] or "—"
        uname = f" @{r['username']}" if r["username"] else ""
        meta = f"{r['language_code'] or '?'} · {r['platform'] or '?'}"
        lines.append(f"• [{r['created_at']}] {who}{uname} ({meta})\n  {r['text']}")
    return "\n".join(lines)


async def reports_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id, settings.admin_id):
        await update.message.reply_text("هذا الأمر للمشرف فقط.")
        return
    conn = connect(settings.db_path)
    init_schema(conn)
    try:
        await update.message.reply_text(format_reports(list_issue_reports(conn)))
    finally:
        conn.close()
```

Register it in `build_application`:
```python
    app.add_handler(CommandHandler("reports", reports_cmd))
```

- [ ] **Step 5: Add `ADMIN_ID` to `.env.example`** — append:

```bash
# Telegram numeric user id allowed to run /reports (0 = disabled)
ADMIN_ID=0
```

- [ ] **Step 6: Run, expect pass** — `cd backend && pytest tests/test_reports.py -q` → passes.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/app/bot.py backend/tests/test_reports.py .env.example
git commit -m "feat(report): ADMIN_ID + admin-gated /reports command"
```

---

### Task 3: `POST /api/report` (TDD)

**Files:** Modify `backend/app/api.py`, `backend/tests/test_reports.py`

**Interfaces:**
- Consumes: `auth.validate_init_data`, `models.insert_issue_report`, `models.list_issue_reports`.
- Produces: `POST /api/report` (header `X-Init-Data`, body `{text, platform?, version?}`) →
  `{"ok": true}`; 401 invalid initData; 400 empty text.

- [ ] **Step 1: Add failing tests** to `backend/tests/test_reports.py` (append; reuse `api_client` + `_init_data` from `test_api.py` via a local copy)

```python
import json, hashlib, hmac
from urllib.parse import urlencode
import pytest
from app import main as main_module
from app.db import connect, init_schema
from app.seed import seed_quiz
from tests.conftest import SAMPLE_DOC

BOT = "123456:TESTTOKEN"


def _init(user):
    fields = {"auth_date": "1700000000", "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


@pytest.fixture
def rep_client(tmp_path, monkeypatch):
    conn = connect(str(tmp_path / "r.db"))
    init_schema(conn)
    seed_quiz(conn, SAMPLE_DOC)
    main_module.app.state.conn = conn
    monkeypatch.setattr(main_module.settings, "bot_token", BOT, raising=False)
    from fastapi.testclient import TestClient
    return TestClient(main_module.app), conn


def test_report_stores_metadata(rep_client):
    client, conn = rep_client
    init = _init({"id": 42, "first_name": "Lina", "username": "lina", "language_code": "ar", "is_premium": True})
    resp = client.post("/api/report", headers={"X-Init-Data": init},
                       json={"text": "زر لا يعمل", "platform": "ios", "version": "7.2"})
    assert resp.status_code == 200 and resp.json() == {"ok": True}
    row = conn.execute("SELECT * FROM issue_reports ORDER BY id DESC LIMIT 1").fetchone()
    assert row["telegram_user_id"] == 42 and row["username"] == "lina"
    assert row["text"] == "زر لا يعمل" and row["platform"] == "ios"
    assert row["language_code"] == "ar" and row["is_premium"] == 1
    assert row["raw_json"] and "42" in row["raw_json"]


def test_report_empty_text_400(rep_client):
    client, _ = rep_client
    init = _init({"id": 42, "first_name": "L"})
    assert client.post("/api/report", headers={"X-Init-Data": init}, json={"text": "  "}).status_code == 400


def test_report_requires_initdata(rep_client):
    client, _ = rep_client
    assert client.post("/api/report", headers={"X-Init-Data": "bad&hash=x"}, json={"text": "hi"}).status_code == 401
```

- [ ] **Step 2: Run, expect fail** — `cd backend && pytest tests/test_reports.py -k report -q` → route 404.

- [ ] **Step 3: Add the route to `backend/app/api.py`** — after `me_dashboard`, before `_now`:

```python
@router.post("/report")
def report(payload: dict, request: Request, x_init_data: str = Header(default="")):
    conn = _conn(request)
    try:
        parsed = validate_init_data(x_init_data, settings.bot_token)
    except AuthError:
        raise HTTPException(401, "invalid initData")
    user = parsed.get("user")
    if not user:
        raise HTTPException(401, "no user in initData")
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "empty report")

    models.insert_issue_report(conn, {
        "telegram_user_id": int(user["id"]),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "language_code": user.get("language_code"),
        "is_premium": int(bool(user.get("is_premium"))),
        "allows_write_to_pm": int(bool(user.get("allows_write_to_pm"))),
        "auth_date": parsed.get("auth_date"),
        "chat_type": parsed.get("chat_type"),
        "chat_instance": parsed.get("chat_instance"),
        "query_id": parsed.get("query_id"),
        "start_param": parsed.get("start_param"),
        "platform": payload.get("platform"),
        "app_version": payload.get("version"),
        "text": text,
        "raw_json": json.dumps(parsed, ensure_ascii=False),
    })
    return {"ok": True}
```

- [ ] **Step 4: Run, expect pass** — `cd backend && pytest tests/test_reports.py -q` → all pass.

- [ ] **Step 5: Full backend suite** — `cd backend && pytest -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api.py backend/tests/test_reports.py
git commit -m "feat(report): POST /api/report stores initData metadata"
```

---

### Task 4: Mini App report screen (TDD)

**Files:** Modify `frontend/index.html`, `frontend/app.js`, `frontend/sprites.js`; Create `frontend/tests/report_ui.test.js`

**Interfaces:**
- Consumes: existing `api`, `tg`, `show`, `sprite`. Produces: a report button on the map + a
  `screen-report` that POSTs `/api/report`.

- [ ] **Step 1: Add a `bug` sprite** to `frontend/sprites.js` — inside `SP`, add:

```javascript
    bug: svg(r(6,2,4,3,T) + r(4,5,8,6,T) + r(5,11,6,2,T) + r(6,6,1,1,I) + r(9,6,1,1,I) + r(3,6,2,1,I) + r(11,6,2,1,I) + r(3,9,2,1,I) + r(11,9,2,1,I) + r(7,5,2,7,I)),
```

- [ ] **Step 2: Add the failing UI test** — `frontend/tests/report_ui.test.js`

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
  window.Telegram = { WebApp: { initData: "INIT", platform: "ios", version: "7.2", ready() {}, expand() {} } };
  const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: async () => ({ ok: true }) }));
  global.fetch = fetchMock;
  const factory = new Function("window", "document", "fetch", appSrc + "\n; return { showReport, show };");
  return { app: factory(window, document, fetchMock), fetchMock };
}

describe("report screen", () => {
  it("POSTs the entered text with the init-data header", async () => {
    const { app, fetchMock } = loadApp();
    app.showReport();
    document.getElementById("report-text").value = "زر لا يعمل";
    document.getElementById("report-send").click();
    await Promise.resolve();
    const call = fetchMock.mock.calls.find((c) => String(c[0]).includes("/api/report"));
    expect(call).toBeTruthy();
    expect(call[1].headers["X-Init-Data"]).toBe("INIT");
    expect(JSON.parse(call[1].body).text).toBe("زر لا يعمل");
  });
});
```

- [ ] **Step 3: Run, expect fail** — `cd frontend && npm test -- report_ui` → `showReport` undefined.

- [ ] **Step 4: Add the report button + screen to `frontend/index.html`** — in `screen-home`'s
`.map-actions`, add a third button:

```html
        <button id="btn-report" class="quiz-card">أبلِغ عن مشكلة</button>
```

After the `screen-progress` section, add:

```html
    <section id="screen-report-issue" class="screen hidden">
      <h2>أبلِغ عن مشكلة</h2>
      <textarea id="report-text" class="report-text" rows="5" placeholder="صف المشكلة أو اقتراحك..."></textarea>
      <div id="report-status"></div>
      <button id="report-send">إرسال</button>
      <button id="report-back">العودة</button>
    </section>
```

(Note: the screen id is `screen-report-issue` to avoid colliding with the existing quiz
`screen-report`.)

- [ ] **Step 5: Register the screen + wire it in `frontend/app.js`**

Add `"report-issue"` to the `screens` array:
```javascript
const screens = ["home", "runner", "report", "board", "badges", "funfact", "progress", "onboarding", "report-issue"];
```

In `renderMap`, after wiring `btn-my-progress`, add:
```javascript
  document.getElementById("btn-report").onclick = showReport;
```

Add the function (near `loadDashboard`):
```javascript
function showReport() {
  const status = document.getElementById("report-status");
  status.textContent = "";
  const ta = document.getElementById("report-text");
  ta.value = "";
  document.getElementById("report-send").onclick = async () => {
    const text = (ta.value || "").trim();
    if (!text) { status.textContent = "اكتب رسالتك أولاً."; return; }
    try {
      await api("/report", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData },
        body: JSON.stringify({ text, platform: tg.platform, version: tg.version }),
      });
      status.textContent = "✅ تم الإرسال، شكراً لك!";
      ta.value = "";
    } catch (e) {
      status.textContent = "تعذّر الإرسال، حاول لاحقاً.";
    }
  };
  document.getElementById("report-back").onclick = loadHome;
  show("report-issue");
}
```

- [ ] **Step 6: Style the textarea** — append to `frontend/styles.css`:

```css
.report-text { width:100%; padding:12px; border:3px solid var(--ink); border-radius:4px;
  background:var(--panel); color:var(--fg); font-family:var(--font-body); font-size:1rem; resize:vertical; }
#report-status { min-height:1.4em; margin:8px 0; color:var(--gold); }
```

- [ ] **Step 7: Run, expect pass** — `cd frontend && npm test -- report_ui` → passes.

- [ ] **Step 8: Full frontend suite + drag e2e**

Run: `cd frontend && npm test && node tests/drag.e2e.mjs`
Expected: all green (`runner.test.js` unaffected — `showReport` only invoked via the map button / test).

- [ ] **Step 9: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/sprites.js frontend/styles.css frontend/tests/report_ui.test.js
git commit -m "feat(report): Mini App report screen + bug sprite"
```

---

### Task 5: Full-suite gate + deploy + migrate

- [ ] **Step 1: Combined suite** — `./scripts/test.sh` → backend (106 + report tests); frontend vitest (31 + report_ui); drag e2e.
- [ ] **Step 2: Deploy + migrate** (schema change; no reseed):

```bash
docker compose up -d --build
sleep 3
docker compose exec -T web python -m app.migrate   # creates issue_reports
```
Verify: `curl -s localhost:8000/health` → ok; `docker compose exec -T web python -c "import sys;sys.path.insert(0,'.');from app.db import connect;print([r[0] for r in connect('/data/quiz.db').execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='issue_reports'\")])"` → `['issue_reports']`.

- [ ] **Step 3: Set `ADMIN_ID`** — tell the owner to add their Telegram numeric id to `.env`
(`ADMIN_ID=<id>`) and `docker compose up -d` (recreate the `bot` service) to enable `/reports`.

---

## Self-Review (completed by plan author)

**Spec coverage:** in-app form POST (§4.5) → Task 4; `POST /api/report` + all metadata (§4.3) →
Task 3; `issue_reports` table + models (§4.1, §4.2) → Task 1; `ADMIN_ID` + `/reports` + gating
(§4.4) → Task 2; one-way (no bot reply) → Tasks 2–4 (only in-app confirmation); deploy + migrate
(§7) → Task 5. ✓

**Placeholder scan:** No "TBD/etc"; every step has concrete code/commands.

**Type consistency:** `insert_issue_report(conn, fields)`/`list_issue_reports(conn, limit)` defined
in Task 1 are consumed in Tasks 2–3; `is_admin`/`format_reports` defined in Task 2 match their
tests; `_REPORT_COLS` keys match the dict assembled in Task 3's route and the columns in Task 1's
DDL. `screen-report-issue` id avoids the existing `screen-report`. `validate_init_data` returns the
parsed dict whose `user`/top-level fields Task 3 reads.

## Out of scope
- Bot-message reporting; attachments; categories; admin web UI.
