# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **Telegram Mini App quiz** that turns four Arabic research-methodology PDFs into gamified
tests. Live at `https://src.mulhamfetna.com` (bot **@src_quize_bot**) via a Cloudflare Tunnel.
The four source PDFs in the repo root are the *curriculum*; the playable content lives in
`content/questions/*.json`.

## Architecture (big picture)

Three processes, one Docker Compose stack (`web` + `bot` + `cloudflared`):

- **Backend** — FastAPI (`backend/app/`), **stdlib `sqlite3` only (no ORM)**. Serves the Mini
  App over HTTPS, exposes a JSON REST API, and persists everything in a SQLite file
  (`QUIZ_DB_PATH`, default `./quiz.db`; in containers `/data/quiz.db` on the `quizdata` volume).
- **Frontend** — a dependency-free RTL-Arabic Mini App (`frontend/index.html`, `app.js`,
  `styles.css`) using Telegram's `telegram-web-app.js`. Single-page, screen-switching via
  `show(name)`; screens are `home/runner/funfact/report/board/badges/progress`.
- **Bot** — `python-telegram-bot` (`backend/app/bot.py`): `/start` opens the Mini App,
  `/leaderboard` posts the overall board, and reports are DM'd after each attempt.

Key backend modules (`backend/app/`): `db` (schema/connection), `models` (queries), `seed`
(load `content/questions/*.json`), `content_schema` (validate a quiz doc), `scoring`
(retry/hint-aware, server-authoritative), `badges`, `notify` (DM via BackgroundTasks),
`migrate` (idempotent schema upgrades), `sampling` (concept-balanced per-attempt sampling),
`progress` (mastery/stats for the dashboard), `auth` (Telegram `initData` HMAC), `api` (routes),
`main` (app + static mounts + cache-busting), `bot`.

### Invariants & gotchas (read before changing behavior)
- **Scoring is server-authoritative.** The client submits `{question_id, retries, hint_used}`;
  the server computes scores. `GET /questions` is unauthenticated and returns a **random,
  concept-balanced sample of ~`SAMPLE_SIZE` (default 10)** questions with answer keys (Khan-style
  client checking — scores are not tamper-proof, an accepted tradeoff).
- **`concept` lives inside `questions.data_json`** (free-form JSON), read in Python — there is
  **no JSON1 dependency** and no `concept` column. Every question must have a non-empty `concept`.
- **Re-seeding wipes attempts.** `seed_quiz` deletes a quiz's existing answers/attempts before
  reinserting, so **leaderboards reset on any content deploy**. Read-only changes need no reseed.
- **Frontend cache-busting is automatic** — `main.py` serves `/app/` dynamically and stamps
  `app.js`/`styles.css` with a `?v=<bundle-sha8>`; never hand-edit the version.
- **Secrets** (`BOT_TOKEN`, `PUBLIC_URL`, `CLOUDFLARE_TUNNEL_TOKEN`) live in a gitignored `.env`.

## Commands

Run from the repo root unless noted.

- **All tests:** `./scripts/test.sh` (backend pytest + frontend Vitest).
- **Backend tests:** `cd backend && pytest -q` (single test: `pytest tests/test_scoring.py::test_name -v`).
- **Frontend tests:** `cd frontend && npm test` (Vitest + jsdom; `npm install` first if needed).
- **Run locally:** `cd backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --reload --port 8000`,
  then open `http://localhost:8000/app/` (submit returns 401 outside Telegram — `initData` is empty).
- **Deploy / update:** `docker compose up -d --build`. After a **schema** change also run
  `docker compose exec -T web python -m app.migrate`. After a **content** change, re-seed:
  `docker compose exec -T web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_all; c=connect('/data/quiz.db'); init_schema(c); print(seed_all(c,'/srv/content/questions'))"`.

## Content

`content/questions/{journals,foundations,paper-types,paper-parts}.json` — one quiz per PDF, ~28
concept-tagged questions each (types: `mcq/tf/image/match/order`). `content/assets/journals/`
holds the only real-artifact screenshots. Synthetic/illustrative questions are allowed when no
real source exists. Validate a file with `app.content_schema.validate_quiz`.

## Design docs

Specs and implementation plans (brainstorm → spec → plan → execute history) live in
`docs/superpowers/{specs,plans}/`. Deployment notes: `docs/DEPLOY.md`.
