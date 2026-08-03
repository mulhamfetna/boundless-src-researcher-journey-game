<div align="center">

# رحلة الباحث — The Researcher's Journey

**A gamified Arabic (RTL) Telegram Mini App that teaches scientific research methodology
by *applying* it, not memorising it.**

<!-- DOI-BADGE -->
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Play it](https://src.mulhamfetna.com) · [@src_quize_bot](https://t.me/src_quize_bot)

</div>

---

## What this is

Most research-methodology teaching asks learners to recall definitions. This one hands them an
artifact and asks them to make a call: *is this journal predatory? where is the gap in this
abstract? which reporting guideline applies? what does Reviewer 2 actually want?*

Every task is **artifact + decision**, never *definition → recall*. Learners climb from the Zaun
undercity to Piltover across six stations and a capstone research journey — a complete cohort study
designed, defended, and revised end to end.

**Six stations** — foundations · journals · paper types · paper parts · publishing requirements ·
submission & tracking — plus **رحلة البحث الكبرى**, the 14-task capstone.

**Interaction types:** multiple choice, true/false, real-screenshot analysis, matching, ordering,
and `spot` (red-flag multi-select). Scoring is retry- and hint-aware; explanations are per-option,
so a wrong answer teaches rather than punishes.

## 📖 Full system handbook

**[`docs/handbook/`](docs/handbook/README.md)** — a complete, diagram-driven explanation of the
whole system: local development, the application internals, the content and scoring engine, the
GitHub workflow, the CI/CD pipeline, the server, data safety, the security model, **every design
decision with the alternatives it beat**, two real incident post-mortems, and a step-by-step guide
to reproducing the entire thing from an empty directory.

## Architecture

Three processes in one Docker Compose stack:

| Component | Stack |
|---|---|
| **Backend** | FastAPI + **stdlib `sqlite3` only** (no ORM). REST API, server-side scoring, badges, progress. |
| **Frontend** | Dependency-free vanilla JS, RTL Arabic, Telegram WebApp SDK. Single page, screen switching. |
| **Bot** | `python-telegram-bot` — opens the Mini App, posts leaderboards, DMs reports. |

Persistence is a single SQLite file on a Docker named volume. Content lives in
`content/questions/*.json`, one concept-tagged document per station.

**Design note:** answer keys are sent to the client and checked there (Khan-Academy style), so
scores are *not* tamper-proof. This is a deliberate trade-off for instant feedback in a teaching
tool, documented rather than hidden.

## Development

```bash
# Run everything
./scripts/test.sh                 # backend pytest + frontend Vitest + browser e2e

# Backend only
cd backend && pytest -q

# Frontend only
cd frontend && npm install && npm test

# Serve locally
cd backend && QUIZ_DB_PATH=../quiz.db uvicorn app.main:app --reload --port 8000
# then open http://localhost:8000/app/
# (submitting returns 401 outside Telegram — initData is empty by design)
```

Local development uses `docker-compose.yml`, which builds the image and bind-mounts `./content`
so content edits appear without a rebuild.

## Deployment

Releases deploy themselves. Publishing a GitHub Release builds a versioned image, pushes it to
GHCR, and a **self-hosted runner on the server** pulls and restarts the stack — no inbound ports,
no SSH from CI, no manual copying.

```
push → GitHub ─┬─ CI: pytest + Vitest on every PR   (GitHub-hosted runners)
               ├─ release published → build image → ghcr.io/…:vX.Y.Z
               └─ deploy → self-hosted runner → docker compose pull && up -d
```

The server runs `docker-compose.prod.yml`, which consumes the published image and holds no source
code. Content is baked into the image, so **content changes ship as a release** — every content
state is a citable version. See [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Contributing

Issues and pull requests are welcome — especially **content corrections**. If a question, answer
key, or explanation is wrong, open a *Content error* issue with a supporting source and it will be
fixed. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Citing

If this work is useful in yours, please cite it — see [`CITATION.cff`](CITATION.cff). Every release
is archived on Zenodo with its own DOI.

## Licence

[AGPL-3.0-or-later](LICENSE). Derivatives must remain open source **including when run as a network
service** — if you host a modified version, your users are entitled to its source.

Course material used to derive the questions is **not** included in this repository; only the
original quiz content authored for this project ships here.
