# Design Spec — Report-an-Issue

**Date:** 2026-06-27
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com

## 1. Purpose

Let a learner report a problem/feedback from inside the Mini App. The report is stored with **all
the metadata Telegram exposes** so the owner can follow up externally (via the reporter's username).
The bot is **not** used for two-way support chat.

## 2. Confirmed decisions (from brainstorming)

| Topic | Decision |
|-------|----------|
| Submission channel | **In-app form only** — a Mini App report screen POSTs to the backend with the Telegram `initData` metadata. |
| Admin access | **Both** — a `/reports` bot command gated by `ADMIN_ID`, **and** the rows in SQLite for ad-hoc queries. |
| Communication | **One-way** — only an in-app "تم الإرسال" confirmation; no bot replies to reports. Owner uses the stored username for follow-up. |
| Auth | `POST /api/report` validates Telegram `initData` (HMAC), same as the other authed endpoints. |

## 3. Architecture (frontend form + backend store + bot admin read)

```
Mini App map → "🐞 أبلِغ عن مشكلة" → report screen (textarea + إرسال)
   POST /api/report  { text, platform, version }  + header X-Init-Data
        │  auth.validate_init_data → trusted user + app fields
        ▼
  models.insert_issue_report(...)  → issue_reports row (SQLite)
        ▲
Bot /reports  (effective_user.id == settings.admin_id)  → latest reports + metadata
```

## 4. Components

### 4.1 Schema — `issue_reports` (`db.py` SCHEMA + `migrate.py`)
Columns: `id PK`, `telegram_user_id`, `username`, `first_name`, `last_name`, `language_code`,
`is_premium`, `allows_write_to_pm`, `auth_date`, `chat_type`, `chat_instance`, `query_id`,
`start_param`, `platform`, `app_version`, `text`, `raw_json`, `created_at`. Added via `db.init_schema`
(`CREATE TABLE IF NOT EXISTS`, auto-created at startup) and an idempotent `migrate.py` entry.

### 4.2 `models.py`
- `insert_issue_report(conn, fields: dict) -> int` — inserts one row (missing keys → NULL/empty),
  `created_at = datetime('now')`.
- `list_issue_reports(conn, limit=20) -> list[Row]` — newest first.

### 4.3 `api.py` — `POST /api/report`
- Validate `initData` (401 on failure / no user). `parsed` already contains `user` (dict) plus
  top-level fields (`auth_date`, `chat_type`, `chat_instance`, `query_id`, `start_param`, …).
- Body: `{ "text": str, "platform": str?, "version": str? }`. Reject empty `text` (400).
- Pull from `parsed["user"]`: `id, username, first_name, last_name, language_code, is_premium,
  allows_write_to_pm`; from `parsed`: `auth_date, chat_type, chat_instance, query_id, start_param`.
  `raw_json = json.dumps(parsed)`. `platform/app_version` from body.
- `insert_issue_report(...)` → `{"ok": true}`.

### 4.4 `bot.py` + `config.py`
- `config.Settings.admin_id: int` from env `ADMIN_ID` (default `0` → disabled).
- `/reports`: if `update.effective_user.id != settings.admin_id` → reply
  "هذا الأمر للمشرف فقط." (and if `admin_id == 0`, always deny). Else format the latest reports
  (each: date, name + @username, lang/premium/platform, text) and reply. A pure
  `format_reports(rows) -> str` helper is unit-testable.

### 4.5 Frontend
- A "🐞 أبلِغ عن مشكلة" button on the map (`screen-home`), opening `screen-report`:
  a textarea (`#report-text`), an "إرسال" button, a back button. On send → `POST /api/report`
  with `X-Init-Data` + `{text, platform: tg.platform, version: tg.version}` → show "✅ تم الإرسال،
  شكراً لك" and return to the map. Arcade-themed; the button uses a sprite (add a `bug` sprite).
- Empty text disables/ignores send.

## 5. Out of scope (YAGNI / future)
- Two-way support chat; bot-message-based reporting; attachments/screenshots; report categories;
  rate limiting beyond what initData's freshness gives; an admin web UI (the `/reports` command +
  DB suffice).

## 6. Testing
- **API:** `POST /api/report` with valid `initData` stores a row carrying the user metadata; empty
  text → 400; missing/invalid `initData` → 401.
- **Models:** `insert_issue_report` + `list_issue_reports` round-trip (newest first, NULL-safe).
- **Bot:** `format_reports(rows)` renders text + username/metadata; admin gating — a helper
  `is_admin(user_id, admin_id)` returns False when `admin_id == 0` or ids differ.
- **Frontend:** Vitest — the report screen POSTs the entered text with the init-data header (fetch
  spied) and shows the confirmation; existing screen/drag tests stay green.

## 7. Deployment
Schema change → after deploy run `python -m app.migrate` (creates `issue_reports` if absent; no
reseed needed). Set `ADMIN_ID` in the gitignored `.env` (owner's Telegram numeric id) to enable
`/reports`. Frontend cache-busts automatically.
