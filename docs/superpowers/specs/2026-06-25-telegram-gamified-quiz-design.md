# Design Spec — Telegram Gamified Quiz for Research-Methodology Sessions

**Date:** 2026-06-25
**Status:** Approved (design); pending implementation plan
**Owner:** xnokia@gmail.com

## 1. Purpose

Turn four Arabic-language research-methodology PDF sessions into a **gamified test** delivered as a **Telegram Mini App + bot**. The goals are:

- A **detailed per-contestant report** after each quiz.
- A **scoreboard / leaderboard** (per-quiz and overall).
- Questions grounded in **real teaching content** from the PDFs.
- **Real-world example artifacts** (screenshots) — genuine public examples that illustrate each concept (e.g. a real legitimate-journal email next to a real predatory-journal email), **not** pictures of the slides.

### Source material (the curriculum)
Four PDFs in the project root (Arabic, real extractable text, ~60 pages total):
1. `أسس البحث العلمي واختيار الفجوة البحثية.pdf` — Foundations of scientific research & choosing the research gap (14 pp).
2. `أنواع الأوراق البحثية العلمية.pdf` — Types of scientific research papers (20 pp).
3. `اجزاء الورقة البحثية.pdf` — Parts of a research paper (9 pp).
4. `المحور الثاني -تصنيف المجلات العلمية.pdf` — Classifying scientific journals (17 pp).

## 2. Confirmed requirements (from brainstorming)

| Decision | Choice |
|----------|--------|
| Platform | Telegram **Mini App** (HTML5/JS in webview) + bot |
| Delivery | **Hybrid**: self-paced (async) first, live timed round later |
| Coverage | **One quiz per PDF** (4 quizzes), each with its own scoreboard; optional combined round later |
| Question authoring | **I draft from the PDFs, user curates** |
| Question types | Multiple choice, True/False, Image-based, Matching/Ordering — **all four** |
| Game mechanics | Points + speed bonus, live leaderboard, streaks & badges, detailed end report — **all** |
| Real artifacts | **I source genuine public examples from the web**; user approves/replaces; I anonymize personal data |
| Language | **Arabic, RTL** |
| Backend | **Python** (FastAPI + python-telegram-bot), deployed via user's Docker host |
| Infra | User has **bot token + HTTPS host** ready |
| Storage | **SQLite** (upgrade path to Postgres) |
| Live realtime | **Polling** first; WebSocket as a future upgrade |

## 3. Architecture (Approach A — Mini App–centric)

```
┌─ Content pipeline (dev-time, offline) ───────────────────────┐
│ pdftotext → teaching points    WebSearch → real artifacts    │
│ → I draft questions/<slug>.json (refs assets) → user curates │
│ → seed.py loads into SQLite                                  │
└───────────────────────────────────────────────────────────────┘
            │ seeds
            ▼
┌─ Backend (Python, FastAPI) ──────────┐     ┌─ Telegram ─────────┐
│ • serves Mini App (HTTPS static)     │◄───►│ Bot (PTB)          │
│ • REST API (quizzes/submit/board)    │     │ /start → open app  │
│ • validates Telegram initData (HMAC) │     │ DMs report, posts  │
│ • scoring engine  • SQLite           │     │ leaderboard, admin │
└───────────────────────────────────────┘     └─────────────────────┘
            ▲ fetch/submit (initData auth)
            │
┌─ Mini App (HTML5/JS, Arabic RTL) ────┐
│ home → quiz runner → report → board  │
│ 4 question types, timer, streaks     │
└───────────────────────────────────────┘
```

### Components & responsibilities
- **Content pipeline** (offline scripts) — extract concepts, source/anonymize real artifacts, produce a curated question bank, seed the DB. Pure data; no runtime dependency.
- **Backend (FastAPI)** — serves the Mini App static files over HTTPS, exposes the REST API, validates Telegram identity, computes scores authoritatively, persists data.
- **Bot (python-telegram-bot)** — entry point (`/start` opens the Mini App), DMs each contestant their report, posts/updates the leaderboard to a group, admin commands to start a live session.
- **Mini App (frontend)** — all gameplay UI: pick quiz, run questions (4 types), per-question feedback, end report, leaderboard. RTL Arabic. Uses the Telegram WebApp SDK for `initData` + theme.

Each unit communicates through a defined interface (JSON over the REST API; the question-bank JSON schema; the Telegram bot API) and is independently testable.

## 4. Data model (SQLite via SQLModel/SQLAlchemy)

- **quizzes** — `id, slug, title_ar, pdf_filename, display_order`
- **questions** — `id, quiz_id, type(mcq|tf|image|match|order), prompt_ar, base_points, explanation_ar, source_page, data(json), display_order`
  - `data` holds type-specific payload: options + correct index (mcq/tf), asset refs + correct (image), pairs (match), correct sequence (order).
- **assets** — `id, quiz_id, question_id?, file_path, kind, source_url, anonymized(bool), caption_ar` — provenance for every real artifact.
- **contestants** — `telegram_user_id(pk), first_name, username, created_at`
- **attempts** — `id, contestant_id, quiz_id, mode(async|live), live_session_id?, total_score, accuracy, duration_ms, started_at, finished_at`
- **answers** — `id, attempt_id, question_id, given(json), is_correct, time_ms, points_awarded`
- **badges** — `id, contestant_id, code, earned_at`
- **live_sessions** — `id, quiz_id, join_code, state(lobby|running|ended), created_at`

## 5. Content & asset pipeline (the "real source" requirement)

1. `scripts/extract.py` → `pdftotext` each PDF to `content/raw/<slug>.txt`; I distill the **teaching points** per session.
2. For each teaching point I author a **question card** needing a real artifact. `WebSearch`/download fetches a **genuine public example** image into `content/assets/<slug>/`, recording its **source URL** and **anonymizing** personal data (blur real names/emails).
3. `content/questions/<slug>.json` references the asset(s), correct answer(s), and an `explanation_ar` tying the real example back to the PDF concept and `source_page`.
4. **User curates/approves** every question and asset before `scripts/seed.py` loads them.

### Question-type → real-artifact mapping
| Type | Real-artifact example |
|------|----------------------|
| Image compare (MCQ) | Real legit-journal email vs. real predatory email → "which is genuine?" |
| Ordering | Real database search-filters screenshot → "rank these filters by importance when choosing a venue" |
| Matching | Match red-flag snippets to their scam-tactic name; match journals to quartile/index |
| True/False | "This indexing badge proves legitimacy" over a real screenshot |
| MCQ / TF (text) | Concept checks grounded in the PDF teaching points |

### Feasibility / risk
I can reliably download **existing** genuine public screenshots (predatory-email samples; DOAJ / Scimago / Beall's-list views are abundant). For any concept where **no good real public artifact exists** (e.g. a paywalled Scopus view that can't be freshly captured), I flag it and ask the user to supply that one. Fetchability is confirmed **early in Phase 1**, not assumed. Web image download requires network access from the sandbox — verified at the start of implementation; if unavailable, assets are sourced by the user and dropped into `content/assets/`.

## 6. Game flow & scoring

- **Per-question score** = `base_points` + **speed bonus** (decays with `time_ms`, bounds-checked server-side) × **streak multiplier** (consecutive-correct grows it; a wrong answer resets it).
- **Scores are authoritative on the server** — the client submits answers + per-question `time_ms`; it never sends its own score. `time_ms` is bounds-checked (anti-cheat is best-effort, acceptable for a learning game).
- **Badges**: `first_complete`, `perfect_quiz`, `streak_5`, `speed_demon` (extensible).
- **End report** (rendered in the Mini App **and** DM'd by the bot): rank, total score, accuracy %, total time, and a per-question review — the contestant's answer vs. correct, `explanation_ar`, and the **real source artifact** + `source_page`.
- **Leaderboard**: per-quiz and overall (configurable: best attempt vs. sum); viewable in the app and postable to a group by the bot.

## 7. Live mode (built on the same engine)

Admin issues a bot command to open a **live session** for a quiz → `join_code`. Contestants join from the Mini App; the app **polls** the leaderboard endpoint (~3 s) for a Kahoot-style shared board. MVP keeps synchronization light (shared live board while everyone plays). **WebSocket push** is a clean future upgrade, not in initial scope.

## 8. Security & correctness

- Backend **validates Telegram `initData` HMAC** (using the bot token) on every API call to trust the contestant's identity — no separate auth.
- All scoring is **server-side**; the client is never trusted for scores.
- Asset provenance (`source_url`) and anonymization are recorded per asset.

## 9. REST API (initial)

- `GET /api/quizzes` — list quizzes.
- `GET /api/quizzes/{slug}/questions` — questions for a quiz (no correct answers leaked).
- `POST /api/quizzes/{slug}/submit` — `{answers:[{question_id, given, time_ms}]}` → server scores, persists attempt, returns the report.
- `GET /api/leaderboard?scope=quiz|overall&slug=` — ranked board.
- `GET /api/me/report?attempt_id=` — fetch a stored report.
- Live: `POST /api/live` (admin create), `POST /api/live/{code}/join`, `GET /api/live/{code}/board`.
- All authenticated via `initData` passed by the Mini App.

## 10. Project layout

```
Gamified-sessions/
  <the 4 PDFs>
  content/
    raw/            # pdftotext output
    questions/      # <slug>.json — drafted by me, curated by user
    assets/<slug>/  # real-world screenshots + provenance
  backend/
    app/  main.py  bot.py  auth.py  api.py  models.py  scoring.py  seed.py
    pyproject.toml  Dockerfile
  frontend/         # Mini App: index.html, js/, css/, assets/
  scripts/  extract.py  render.py
  tests/            # pytest: scoring, initData auth, API, seed integrity
  docker-compose.yml
  .env              # BOT_TOKEN, PUBLIC_URL, ... (gitignored)
  docs/superpowers/specs/
```

## 11. Build phasing

- **Phase 1 — vertical slice**: self-paced, **one** quiz end-to-end (extract → real assets → curated JSON → seed → API → Mini App runner → server scoring → report → simple leaderboard). Confirms artifact fetchability and the whole pipeline.
- **Phase 2 — full content & mechanics**: all 4 quizzes, all 4 question types, streaks, badges, per-quiz + overall leaderboards, bot DM reports.
- **Phase 3 — live mode**: admin live sessions, join codes, polled shared leaderboard.

## 12. Testing & quality

- **TDD** on the pure logic: `scoring.py` (base + speed + streak, edge cases), `auth.py` (`initData` HMAC validation — valid/expired/tampered), seed integrity (every question's assets exist; correct-answer indices in range).
- API endpoint tests (FastAPI `TestClient`).
- Manual playthrough of the Mini App per phase.

## 13. Open items to confirm during implementation

- Sandbox **network access** for web image download (else user supplies assets).
- Exact **leaderboard aggregation** rule (best vs. sum) — default: **best attempt per quiz**, overall = sum of bests.
- Whether a **combined "final boss"** quiz across all 4 PDFs is wanted (deferred; not in phases 1–3).
- Hosting specifics (domain, webhook vs. long-polling for the bot) — captured at deploy time.
```
