# CI/CD + Open-Source Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the project as a professional AGPL-3.0 open-source repo with a Zenodo DOI, and make every GitHub Release deploy itself to the shared Ubuntu server with no manual rsync and no inbound network access.

**Architecture:** GitHub Actions builds a versioned container image and pushes it to GHCR. A self-hosted runner *on the server* holds an outbound connection to GitHub and, on `release: published` only, pulls that image and restarts the compose stack. The server holds no source code — only `docker-compose.prod.yml`, `.env`, and the `quizdata` volume.

**Tech Stack:** GitHub Actions, GHCR (ghcr.io), Docker Compose, FastAPI + stdlib `sqlite3`, Vitest, pytest, Zenodo.

## Global Constraints

- Repo: `mulhamfetna/boundless-src-researcher-journey-game`, **public**, **AGPL-3.0**.
- **SQLite stays.** No ORM, no Postgres, no rewrite of `models.py`.
- The self-hosted runner **never** runs on `pull_request` — only `release: published` and `workflow_dispatch`.
- **No inbound ports, no firewall changes** on the shared server. Outbound HTTPS only.
- `.env` lives only on the server (`chmod 600`). Never committed, never echoed in a workflow.
- No GitHub secrets beyond the automatic `GITHUB_TOKEN`.
- The six root `*.pdf` curriculum files are excluded from the repo.
- Author metadata: Mulham Fetna, ORCID `0009-0006-4432-798X`, `contact@mulhamfetna.com`.
- Conventional commits; semantic version tags `vX.Y.Z`.

---

### Task 1: Repo hygiene + open-source scaffolding

**Files:**
- Modify: `.gitignore`
- Create: `LICENSE`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CITATION.cff`, `.zenodo.json`
- Create: `.github/ISSUE_TEMPLATE/{bug_report,feature_request,content_error}.yml`, `.github/pull_request_template.md`, `.github/dependabot.yml`

**Interfaces:**
- Consumes: nothing.
- Produces: a repo that is safe and complete to publish. Task 6 pushes it.

- [ ] **Step 1: Exclude the curriculum PDFs**

Append to `.gitignore`:

```gitignore

# Third-party curriculum PDFs (course material — not ours to redistribute)
*.pdf
```

- [ ] **Step 2: Verify nothing sensitive would be published**

```bash
git status --porcelain | grep '^??' || true
git ls-files | grep -iE '\.env|\.db|node_modules|\.pdf$' && echo "LEAK" || echo "clean"
```
Expected: `clean`, and no `*.pdf` in the untracked list.

- [ ] **Step 3: Add the AGPL-3.0 license**

```bash
curl -fsSL https://www.gnu.org/licenses/agpl-3.0.txt -o LICENSE
head -3 LICENSE   # expect: GNU AFFERO GENERAL PUBLIC LICENSE / Version 3
```

- [ ] **Step 4: Write `CITATION.cff`**

```yaml
cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "رحلة الباحث — The Researcher's Journey"
abstract: >-
  A gamified Arabic (RTL) Telegram Mini App that teaches scientific research
  methodology through hands-on application tasks rather than recall.
type: software
authors:
  - given-names: Mulham
    family-names: Fetna
    email: contact@mulhamfetna.com
    orcid: "https://orcid.org/0009-0006-4432-798X"
license: AGPL-3.0-or-later
repository-code: "https://github.com/mulhamfetna/boundless-src-researcher-journey-game"
keywords:
  - research methodology
  - gamification
  - Telegram Mini App
  - Arabic
  - education
```

- [ ] **Step 5: Write `.zenodo.json`**

```json
{
  "title": "رحلة الباحث — The Researcher's Journey",
  "description": "A gamified Arabic (RTL) Telegram Mini App teaching scientific research methodology through applied tasks.",
  "license": "AGPL-3.0-or-later",
  "upload_type": "software",
  "creators": [
    {
      "name": "Fetna, Mulham",
      "orcid": "0009-0006-4432-798X"
    }
  ],
  "keywords": ["research methodology", "gamification", "Telegram Mini App", "Arabic", "education"]
}
```

- [ ] **Step 6: Write `README.md`**

Must contain: one-line description, live URL `https://src.mulhamfetna.com`, bot `@src_quize_bot`, the DOI badge placeholder line `<!-- DOI-BADGE -->` (Task 8 replaces it), architecture summary (FastAPI + stdlib sqlite3 + vanilla-JS RTL frontend + PTB bot), local dev commands (`./scripts/test.sh`, the uvicorn command from `CLAUDE.md`), deployment summary (release → GHCR → self-hosted runner), and a licence section naming AGPL-3.0.

- [ ] **Step 7: Write `CONTRIBUTING.md`**

Must document: open an issue first; branch naming `feat/<issue#>-<slug>` / `fix/<issue#>-<slug>`; PRs target `dev`; `dev` → `main` for release; conventional commit format; `./scripts/test.sh` must pass; content changes require a release because content is baked into the image.

- [ ] **Step 8: Write `SECURITY.md`**

Must state: report privately via GitHub Security Advisories or `contact@mulhamfetna.com`; do not open public issues for vulnerabilities; note that scores are client-checked by design (documented trade-off, not a vulnerability).

- [ ] **Step 9: Add the content-error issue template**

`.github/ISSUE_TEMPLATE/content_error.yml`:

```yaml
name: Content error
description: A question, answer key, or explanation is wrong or unclear
title: "[content] "
labels: ["content"]
body:
  - type: input
    id: station
    attributes:
      label: Station (quiz slug)
      placeholder: journals / foundations / capstone / ...
    validations:
      required: true
  - type: textarea
    id: problem
    attributes:
      label: What is wrong?
    validations:
      required: true
  - type: textarea
    id: source
    attributes:
      label: Source supporting the correction
      description: A citation, standard (ICMJE/COPE/PRISMA/STROBE), or link.
```

Create `bug_report.yml` and `feature_request.yml` in the same style (fields: what happened / expected / steps; and problem / proposed solution).

- [ ] **Step 10: Add `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule: { interval: "weekly" }
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule: { interval: "weekly" }
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
```

- [ ] **Step 11: Add `.github/pull_request_template.md`**

Checklist: linked issue, conventional-commit title, `./scripts/test.sh` passes, docs updated, content change → needs release.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "docs: AGPL-3.0 licence, citation metadata, and contributor scaffolding"
```

---

### Task 2: `meta` table + per-quiz content hashing

Prevents the deploy from wiping leaderboards. Verified problem: `backend/app/seed.py:18-24` deletes a quiz's answers/attempts on every reseed.

**Files:**
- Modify: `backend/app/db.py` (SCHEMA), `backend/app/migrate.py`, `backend/app/seed.py`
- Test: `backend/tests/test_seed_changed.py`

**Interfaces:**
- Produces:
  - `app.seed.file_sha256(path: str) -> str`
  - `app.seed.seed_changed(conn, dir: str = "content/questions", force: bool = False) -> dict` returning `{"seeded": [slug, ...], "skipped": [slug, ...]}`
  - `meta` table: `key TEXT PRIMARY KEY, value TEXT NOT NULL`; content keys are `content_sha:<slug>`.
- Consumed by: Task 5's deploy job.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_seed_changed.py`:

```python
import json
import os

from app.db import connect, init_schema
from app.seed import seed_changed


def _doc(slug, prompt="ما هي الفجوة البحثية؟"):
    return {
        "slug": slug,
        "title_ar": "اختبار",
        "pdf_filename": "x.pdf",
        "fun_facts_ar": [],
        "questions": [
            {
                "type": "tf",
                "prompt_ar": prompt,
                "options_ar": ["صح", "خطأ"],
                "correct_index": 0,
                "concept": "gap",
                "explanation_ar": "شرح",
            }
        ],
    }


def _write(dirpath, slug, prompt="ما هي الفجوة البحثية؟"):
    path = os.path.join(dirpath, f"{slug}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_doc(slug, prompt), f, ensure_ascii=False)
    return path


def test_first_run_seeds_then_second_run_skips(tmp_path):
    conn = connect(":memory:")
    init_schema(conn)
    d = str(tmp_path)
    _write(d, "alpha")

    first = seed_changed(conn, d)
    assert first["seeded"] == ["alpha"]
    assert first["skipped"] == []

    second = seed_changed(conn, d)
    assert second["seeded"] == []
    assert second["skipped"] == ["alpha"]


def test_only_the_changed_quiz_is_reseeded(tmp_path):
    conn = connect(":memory:")
    init_schema(conn)
    d = str(tmp_path)
    _write(d, "alpha")
    _write(d, "beta")
    seed_changed(conn, d)

    _write(d, "beta", prompt="سؤال مختلف تمامًا")
    result = seed_changed(conn, d)

    assert result["seeded"] == ["beta"]
    assert result["skipped"] == ["alpha"]


def test_unchanged_quiz_keeps_its_attempts(tmp_path):
    conn = connect(":memory:")
    init_schema(conn)
    d = str(tmp_path)
    _write(d, "alpha")
    seed_changed(conn, d)

    quiz_id = conn.execute("SELECT id FROM quizzes WHERE slug='alpha'").fetchone()["id"]
    conn.execute("INSERT INTO contestants (telegram_id, display_name) VALUES (?, ?)", (1, "Vi"))
    cid = conn.execute("SELECT id FROM contestants").fetchone()["id"]
    conn.execute(
        "INSERT INTO attempts (quiz_id, contestant_id, score) VALUES (?, ?, ?)",
        (quiz_id, cid, 100),
    )
    conn.commit()

    seed_changed(conn, d)   # no content change

    assert conn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"] == 1


def test_force_reseeds_everything(tmp_path):
    conn = connect(":memory:")
    init_schema(conn)
    d = str(tmp_path)
    _write(d, "alpha")
    seed_changed(conn, d)

    result = seed_changed(conn, d, force=True)
    assert result["seeded"] == ["alpha"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && pytest tests/test_seed_changed.py -v`
Expected: FAIL with `ImportError: cannot import name 'seed_changed' from 'app.seed'`.

- [ ] **Step 3: Add the `meta` table to the schema (fresh databases)**

In `backend/app/db.py`, inside the `SCHEMA` string, add alongside the other tables:

```sql
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

- [ ] **Step 4: Add the idempotent migration (existing databases)**

In `backend/app/migrate.py`, inside `migrate(conn)` before the final `conn.commit()`, following the existing style used for the `duels` table:

```python
    has_meta = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if not has_meta:
        conn.executescript(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        )
        changes.append("meta")
```

- [ ] **Step 5: Implement hashing and conditional seeding**

In `backend/app/seed.py`, add at the top: `import hashlib`. Then append:

```python
def file_sha256(path: str) -> str:
    """Content hash of a quiz file, used to decide whether a reseed is needed."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def seed_changed(
    conn: sqlite3.Connection, dir: str = "content/questions", force: bool = False
) -> dict:
    """Seed only quizzes whose JSON changed since the last run.

    Reseeding a quiz deletes its attempts (see seed_quiz), so unconditional
    seeding on every deploy would wipe every leaderboard. Hashing per file keeps
    untouched stations intact.
    """
    seeded, skipped = [], []
    for path in sorted(glob.glob(os.path.join(dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        slug = doc["slug"]
        key = f"content_sha:{slug}"
        sha = file_sha256(path)
        if not force and _get_meta(conn, key) == sha:
            skipped.append(slug)
            continue
        seed_quiz(conn, doc)
        _set_meta(conn, key, sha)
        seeded.append(slug)
    conn.commit()
    return {"seeded": seeded, "skipped": skipped}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_seed_changed.py -v`
Expected: 4 passed.

- [ ] **Step 7: Run the whole suite for regressions**

Run: `./scripts/test.sh`
Expected: all backend + frontend suites pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/db.py backend/app/migrate.py backend/app/seed.py backend/tests/test_seed_changed.py
git commit -m "feat(seed): per-quiz content hashing so deploys no longer wipe leaderboards"
```

---

### Task 3: Production compose file

**Files:**
- Create: `docker-compose.prod.yml`
- Modify: `docs/DEPLOY.md`

**Interfaces:**
- Consumes: the image name `ghcr.io/mulhamfetna/boundless-src-researcher-journey-game`.
- Produces: the compose file Task 5's deploy job and Task 7's server setup both use.

- [ ] **Step 1: Create `docker-compose.prod.yml`**

Note the differences from the dev file: `image:` instead of `build:`, **no `./content` bind mount** (content is baked into the image), and no host port publishing (Cloudflare reaches `web` over the compose network).

```yaml
# Production stack. The server holds only this file, .env, and the quizdata
# volume — no source code. Deployed by .github/workflows/release.yml.
services:
  web:
    image: ${APP_IMAGE:-ghcr.io/mulhamfetna/boundless-src-researcher-journey-game:latest}
    restart: unless-stopped
    env_file: .env
    environment:
      QUIZ_DB_PATH: /data/quiz.db
    volumes:
      - quizdata:/data
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

  bot:
    image: ${APP_IMAGE:-ghcr.io/mulhamfetna/boundless-src-researcher-journey-game:latest}
    restart: unless-stopped
    env_file: .env
    environment:
      QUIZ_DB_PATH: /data/quiz.db
    volumes:
      - quizdata:/data
    command: ["python", "-m", "app.bot"]

  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      - web

volumes:
  quizdata:
```

- [ ] **Step 2: Verify the file parses**

Run: `APP_IMAGE=x CLOUDFLARE_TUNNEL_TOKEN=x docker compose -f docker-compose.prod.yml config >/dev/null && echo OK`
Expected: `OK`.

- [ ] **Step 3: Document the two compose files in `docs/DEPLOY.md`**

Add a section stating: `docker-compose.yml` is for local development (builds locally, bind-mounts `./content` for instant content edits); `docker-compose.prod.yml` runs on the server from a published image and has no bind mount, so content ships only via a release.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.prod.yml docs/DEPLOY.md
git commit -m "feat(ops): production compose file consuming the published GHCR image"
```

---

### Task 4: CI workflow (tests on every PR)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: status checks named `backend` and `frontend`, required by Task 6's branch protection.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main, dev]

permissions:
  contents: read

jobs:
  backend:
    runs-on: ubuntu-latest        # GitHub-hosted: safe for untrusted PR code
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: pip install -e ./backend pytest
      - name: Test
        working-directory: backend
        run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install
        working-directory: frontend
        run: npm ci
      - name: Test
        working-directory: frontend
        run: npm test
```

- [ ] **Step 2: Verify the workflow is valid YAML**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('valid')"`
Expected: `valid`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run backend and frontend suites on every pull request"
```

---

### Task 5: Release + deploy + rollback workflows

**Files:**
- Create: `.github/workflows/release.yml`, `.github/workflows/rollback.yml`

**Interfaces:**
- Consumes: `app.seed.seed_changed` (Task 2), `docker-compose.prod.yml` (Task 3).
- Produces: images `ghcr.io/mulhamfetna/boundless-src-researcher-journey-game:<tag>` and `:latest`.

- [ ] **Step 1: Create `.github/workflows/release.yml`**

The `deploy` job is the only one that runs on the server. It is gated to `release: published`, which only a maintainer can trigger — a fork PR can never reach it.

```yaml
name: Release

on:
  release:
    types: [published]

permissions:
  contents: read
  packages: write

env:
  IMAGE: ghcr.io/${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest        # GitHub-hosted
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ${{ env.IMAGE }}:${{ github.event.release.tag_name }}
            ${{ env.IMAGE }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: self-hosted          # the shared server; outbound connection only
    environment: production
    steps:
      - name: Pull and start the released image
        working-directory: /opt/researcher-journey
        env:
          APP_IMAGE: ${{ env.IMAGE }}:${{ github.event.release.tag_name }}
        run: |
          set -euo pipefail
          echo "$APP_IMAGE" > .image-next
          docker compose -f docker-compose.prod.yml pull
          docker compose -f docker-compose.prod.yml up -d

      - name: Migrate schema (idempotent)
        working-directory: /opt/researcher-journey
        run: docker compose -f docker-compose.prod.yml exec -T web python -m app.migrate

      - name: Seed only changed content
        working-directory: /opt/researcher-journey
        run: |
          docker compose -f docker-compose.prod.yml exec -T web python -c "
          import sys; sys.path.insert(0, '.')
          from app.db import connect, init_schema
          from app.seed import seed_changed
          c = connect('/data/quiz.db'); init_schema(c)
          print(seed_changed(c, '/srv/content/questions'))
          "

      - name: Smoke test
        run: |
          set -euo pipefail
          for i in $(seq 1 15); do
            if curl -fsS http://localhost:8000/api/quizzes >/dev/null; then
              echo "api ok"; break
            fi
            [ "$i" = "15" ] && { echo "api never came up"; exit 1; }
            sleep 2
          done
          curl -fsS -o /dev/null http://localhost:8000/content/assets/art/map_bg.png
          echo "assets ok"

      - name: Roll back on failure
        if: failure()
        working-directory: /opt/researcher-journey
        run: |
          echo "Deploy failed — restoring the previous image."
          if [ -f .image-current ]; then
            APP_IMAGE="$(cat .image-current)" docker compose -f docker-compose.prod.yml up -d
          fi
          exit 1

      - name: Record the deployed image
        working-directory: /opt/researcher-journey
        run: mv .image-next .image-current
```

Note: the smoke test's `curl` to `localhost:8000` requires the `web` service to publish that port on the server. Task 7 Step 4 adds a `ports: ["127.0.0.1:8000:8000"]` override bound to loopback only — reachable by the runner, never by the network.

- [ ] **Step 2: Create `.github/workflows/rollback.yml`**

```yaml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      tag:
        description: "Image tag to roll back to (e.g. v1.0.0)"
        required: true

permissions:
  contents: read

jobs:
  rollback:
    runs-on: self-hosted
    environment: production
    steps:
      - name: Start the requested tag
        working-directory: /opt/researcher-journey
        env:
          APP_IMAGE: ghcr.io/${{ github.repository }}:${{ inputs.tag }}
        run: |
          set -euo pipefail
          docker compose -f docker-compose.prod.yml pull
          docker compose -f docker-compose.prod.yml up -d
          echo "$APP_IMAGE" > .image-current
      - name: Smoke test
        run: curl -fsS http://localhost:8000/api/quizzes >/dev/null && echo ok
```

- [ ] **Step 3: Validate both workflows**

```bash
python - <<'PY'
import yaml
for f in [".github/workflows/release.yml", ".github/workflows/rollback.yml"]:
    yaml.safe_load(open(f)); print("valid:", f)
PY
```
Expected: both valid.

- [ ] **Step 4: Verify the runner is never exposed to PR code**

```bash
grep -n "runs-on: self-hosted" -B12 .github/workflows/*.yml | grep -E "^\S+[-:]\s*(on|pull_request)" || true
grep -c "pull_request" .github/workflows/release.yml .github/workflows/rollback.yml
```
Expected: `0` occurrences of `pull_request` in both files.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yml .github/workflows/rollback.yml
git commit -m "ci: build to GHCR on release and deploy via the self-hosted runner"
```

---

### Task 6: Branch model + create and push the public repo

**Files:** none (git and GitHub configuration).

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: the public repo, `main` + `dev` branches, protection rules, and the `production` environment used by Task 5.

- [ ] **Step 1: Rotate the bot token first**

Open `@BotFather` → `/revoke` → `/token` for `@src_quize_bot`, then update `BOT_TOKEN` in the local `.env`. The old token appeared in a chat transcript. **Do not proceed until this is done.**

- [ ] **Step 2: Rename `master` to `main` and create `dev`**

```bash
git branch -m master main
git branch dev
git branch          # expect: dev, * main
```

- [ ] **Step 3: Create the public repo and push**

```bash
gh repo create boundless-src-researcher-journey-game \
  --public \
  --source=. \
  --remote=origin \
  --description "رحلة الباحث — a gamified Arabic Telegram Mini App teaching scientific research methodology" \
  --push
git push -u origin dev
```

- [ ] **Step 4: Verify what actually got published**

```bash
gh repo view --json name,visibility,licenseInfo
git ls-remote --heads origin
gh api repos/:owner/:repo/contents --jq '.[].name' | grep -iE '\.env|\.pdf' && echo "LEAK" || echo "clean"
```
Expected: visibility `PUBLIC`, licence AGPL-3.0, branches `main` and `dev`, and `clean`.

- [ ] **Step 5: Protect both branches**

```bash
for BR in main dev; do
  gh api -X PUT repos/:owner/:repo/branches/$BR/protection \
    -H "Accept: application/vnd.github+json" \
    -f "required_status_checks[strict]=true" \
    -f "required_status_checks[contexts][]=backend" \
    -f "required_status_checks[contexts][]=frontend" \
    -F "enforce_admins=false" \
    -F "required_pull_request_reviews[required_approving_review_count]=0" \
    -F "restrictions=null"
done
```

- [ ] **Step 6: Create the `production` environment**

```bash
gh api -X PUT repos/:owner/:repo/environments/production
```

- [ ] **Step 7: Commit any local changes and verify CI runs**

```bash
git checkout -b chore/verify-ci dev
git commit --allow-empty -m "chore: verify CI wiring"
git push -u origin chore/verify-ci
gh pr create --base dev --title "chore: verify CI wiring" --body "Confirms backend and frontend checks run."
gh pr checks --watch
```
Expected: both `backend` and `frontend` checks pass. Then merge and delete the branch.

---

### Task 7: Server setup (runbook — run on the Ubuntu server)

These steps are executed by the user on the shared server. Nothing here opens a port or changes networking.

**Files:**
- Create on server: `/opt/researcher-journey/{docker-compose.prod.yml,.env,docker-compose.override.yml}`, `/etc/systemd/system/quiz-backup.{service,timer}`

- [ ] **Step 1: Create a dedicated user and directory**

```bash
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
sudo mkdir -p /opt/researcher-journey /var/backups/quiz
sudo chown -R deploy:deploy /opt/researcher-journey /var/backups/quiz
```

- [ ] **Step 2: Install the self-hosted runner**

In the browser: repo → **Settings → Actions → Runners → New self-hosted runner → Linux x64**. GitHub shows a download and a `./config.sh` command containing a one-time token. As the `deploy` user:

```bash
sudo -iu deploy
mkdir -p ~/actions-runner && cd ~/actions-runner
# paste the download + tar commands GitHub displayed, then:
./config.sh --url https://github.com/mulhamfetna/boundless-src-researcher-journey-game \
            --token <TOKEN-FROM-GITHUB> --labels self-hosted,linux,x64 --unattended
exit
sudo ~deploy/actions-runner/svc.sh install deploy
sudo ~deploy/actions-runner/svc.sh start
sudo ~deploy/actions-runner/svc.sh status     # expect: active (running)
```

This connects **outbound** to GitHub. No inbound port is opened.

- [ ] **Step 3: Create `.env` on the server**

```bash
sudo -iu deploy
cd /opt/researcher-journey
cat > .env <<'EOF'
BOT_TOKEN=<the NEW rotated token>
CLOUDFLARE_TUNNEL_TOKEN=<tunnel token>
ADMIN_ID=5041591927
PUBLIC_URL=https://src.mulhamfetna.com
EOF
chmod 600 .env
```

- [ ] **Step 4: Copy the compose file and add a loopback port override**

Copy `docker-compose.prod.yml` from the repo to `/opt/researcher-journey/`. Then create `docker-compose.override.yml` so the runner's smoke test can reach the API without exposing it to the network:

```yaml
services:
  web:
    ports:
      - "127.0.0.1:8000:8000"   # loopback only — not reachable off-host
```

- [ ] **Step 5: Migrate the existing database so leaderboards carry over**

On the laptop:

```bash
docker compose exec -T web sqlite3 /data/quiz.db ".backup /tmp/quiz.db"
docker compose cp web:/tmp/quiz.db ./quiz-migrate.db
scp quiz-migrate.db deploy@<server>:/tmp/quiz.db
```

On the server:

```bash
cd /opt/researcher-journey
docker compose -f docker-compose.prod.yml up -d web    # creates the volume
docker compose -f docker-compose.prod.yml cp /tmp/quiz.db web:/data/quiz.db
docker compose -f docker-compose.prod.yml restart web
```

- [ ] **Step 6: Verify the volume survives a container reset**

```bash
docker compose -f docker-compose.prod.yml exec -T web sqlite3 /data/quiz.db "SELECT COUNT(*) FROM attempts;"
docker compose -f docker-compose.prod.yml down          # NOTE: never use -v
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec -T web sqlite3 /data/quiz.db "SELECT COUNT(*) FROM attempts;"
```
Expected: the two counts are identical. This is the proof that data survives container resets.

- [ ] **Step 7: Install the nightly backup timer**

`/etc/systemd/system/quiz-backup.service`:

```ini
[Unit]
Description=Backup the quiz SQLite database

[Service]
Type=oneshot
User=deploy
WorkingDirectory=/opt/researcher-journey
ExecStart=/bin/bash -c 'docker compose -f docker-compose.prod.yml exec -T web sqlite3 /data/quiz.db ".backup /tmp/b.db" && docker compose -f docker-compose.prod.yml cp web:/tmp/b.db /var/backups/quiz/quiz-$(date +%%F).db && find /var/backups/quiz -name "quiz-*.db" -mtime +14 -delete'
```

`/etc/systemd/system/quiz-backup.timer`:

```ini
[Unit]
Description=Nightly quiz database backup

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quiz-backup.timer
sudo systemctl start quiz-backup.service
ls -la /var/backups/quiz/          # expect one dated .db file
```

- [ ] **Step 8: Point the Cloudflare tunnel at the server**

The tunnel token in `.env` is the same connector; running `cloudflared` on the server registers a new connector for the tunnel. Once it is healthy, stop the stack on the laptop so only the server serves traffic:

```bash
# on the laptop, after confirming the server is serving:
docker compose down
```

---

### Task 8: First release, Zenodo DOI, and end-to-end verification

- [ ] **Step 1: Enable the Zenodo integration**

Sign in at <https://zenodo.org> with GitHub → **Settings → GitHub** → toggle **ON** for `boundless-src-researcher-journey-game`. The toggle must be enabled *before* the release that should mint the DOI.

- [ ] **Step 2: Merge `dev` into `main` and cut the release**

```bash
gh pr create --base main --head dev --title "release: v1.0.0" --body "First public release."
gh pr merge --merge --delete-branch=false
gh release create v1.0.0 --target main --generate-notes \
  --title "v1.0.0 — first public release"
```

- [ ] **Step 3: Watch the pipeline**

```bash
gh run watch
```
Expected: `build` succeeds on the GitHub-hosted runner, then `deploy` succeeds on the self-hosted runner, including the smoke test.

- [ ] **Step 4: Verify the deployment is live and is the new version**

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' https://src.mulhamfetna.com/api/quizzes
curl -fsS -o /dev/null -w '%{http_code}\n' https://src.mulhamfetna.com/content/assets/art/map_bg.png?v=2
```
Expected: `200` and `200`.

- [ ] **Step 5: Verify leaderboards survived the deploy**

```bash
curl -fsS "https://src.mulhamfetna.com/api/leaderboard?scope=overall" | head -c 300
```
Expected: the same contestants as before the migration — proving `seed_changed` skipped unchanged content.

- [ ] **Step 6: Add the DOI badge**

Copy the DOI from the Zenodo record, then replace the `<!-- DOI-BADGE -->` line in `README.md`:

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

```bash
git checkout -b docs/doi-badge dev
git add README.md
git commit -m "docs: add Zenodo DOI badge"
git push -u origin docs/doi-badge
gh pr create --base dev --title "docs: add Zenodo DOI badge" --body "Adds the minted DOI."
```

- [ ] **Step 7: Verify rollback works**

Run the `Rollback` workflow from the Actions tab with tag `v1.0.0`, confirm it succeeds, then re-run the latest release deploy. This proves the recovery path *before* you need it.

---

## Self-Review

**Spec coverage:** §3 architecture → Tasks 3, 5, 7. §4 security model → Task 5 Steps 1/4, Task 6 Step 6. §5 data safety → Task 2 (hashing), Task 7 Steps 5–7 (volume proof + backups). §6 content baking → Task 3. §7 scaffolding + branch model → Tasks 1, 6. §8 workflows → Tasks 4, 5. §9 secrets → Task 6 Step 1, Task 7 Step 3. §10 exclusions → Task 1 Steps 1–2. §11 migration path → Tasks 6–8. §12 verification → Task 8. No gaps.

**Placeholders:** none. `<TOKEN-FROM-GITHUB>`, `<server>`, and `10.5281/zenodo.XXXXXXX` are values that can only exist at runtime; each step says exactly where to obtain them.

**Type consistency:** `seed_changed(conn, dir, force)` returning `{"seeded": [...], "skipped": [...]}` is defined in Task 2 and consumed identically in Task 5. `meta(key, value)` matches between `db.py` (Task 2 Step 3) and `migrate.py` (Step 4). `APP_IMAGE` is consistent across Task 3, Task 5, and Task 7.
