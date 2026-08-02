# CI/CD + open-source release — design

**Date:** 2026-07-29
**Status:** approved (brainstormed with the user, 2026-07-29)
**Repo:** `mulhamfetna/boundless-src-researcher-journey-game` (public, AGPL-3.0)

---

## 1. Goals

1. **Never rsync again.** Pushing a release deploys the app to the server automatically.
2. **Touch no network config.** The server is *shared*; no open ports, no firewall rules, no
   port-forwarding, no inbound anything.
3. **Professional open-source project** — AGPL-3.0, citable via Zenodo DOI, issue/PR/release
   workflow, protected branches, CI on every change.
4. **Data survives everything** except deliberate destruction, and is backed up.

## 2. Non-goals

- No ORM, no Postgres, no database migration. **SQLite stays.** (The earlier ORM discussion applied
  only to serverless hosts with ephemeral disks; on an owned server it is irrelevant.)
- No Kubernetes, no multi-node orchestration, no blue/green. One server, one compose stack.
- No secrets in GitHub beyond the automatic `GITHUB_TOKEN`.

## 3. Architecture — pull-based deployment

```
laptop ──push──> GitHub ──┬─ ci.yml       (GitHub-hosted)  pytest + vitest on every PR
                          ├─ release.yml  (GitHub-hosted)  build image -> GHCR :vX.Y.Z + :latest
                          └─ deploy job   (SELF-HOSTED, on the server)
                                             docker compose pull && up -d && migrate && smoke
```

The server runs a **self-hosted GitHub Actions runner** that maintains an *outbound* HTTPS long-poll
to GitHub. GitHub never connects inward. This satisfies the shared-server constraint completely and
is why it is preferred over the SSH-push and Gitea/GitLab-webhook alternatives the user considered.

**The server never contains source code.** It holds only:

```
/opt/researcher-journey/
  docker-compose.prod.yml    # image: ghcr.io/... ; no build: section
  .env                       # chmod 600, secrets, never in git
  (docker named volume: quizdata)
```

Deployment = `docker compose pull && docker compose up -d`. The artifact is an immutable, versioned
image, so a deploy is atomic and a rollback is just an older tag.

## 4. Security model (public repo + self-hosted runner)

GitHub explicitly warns against self-hosted runners on public repos: a fork's pull request could
execute arbitrary code on the runner. Mitigated by **separating trust levels per event**:

| Job | Runner | Trigger | Runs untrusted code? |
|-----|--------|---------|----------------------|
| test | GitHub-hosted (disposable) | `pull_request`, `push` | Yes — safely sandboxed by GitHub |
| build+push image | GitHub-hosted | `release: published` | No |
| **deploy** | **self-hosted (the server)** | **`release: published` only** | **No** |

Rules, all enforced in the workflow files:

- The self-hosted job **never** runs on `pull_request`. Only `release: published` and a manually
  dispatched rollback.
- It is bound to a GitHub **Environment (`production`)**, which restricts it to protected branches
  and allows an optional required reviewer.
- The deploy job runs a **fixed script** — pull, up, migrate, smoke-test. It does not build, does not
  run repo-provided scripts, and does not evaluate PR-authored code.
- Runner OS user: non-root, member of `docker` group, `$HOME` isolated from other server users.

## 5. Data safety

- **`quizdata` named volume** already isolates the DB from the container lifecycle. Rebuilds, image
  swaps, `docker compose down`, and container resets all preserve it. Only `down -v` destroys it —
  the deploy script never uses `-v`.
- **Nightly backup:** `sqlite3 /data/quiz.db ".backup /backups/quiz-$(date +%F).db"` via a systemd
  timer, 14-day retention. `.backup` is safe against a live writer; `cp` is not.
- **Seeding must not run blindly.** Verified in `backend/app/seed.py:18-24`: seeding a quiz deletes
  that quiz's `answers`, `attempts`, `assets`, `questions`, and `quizzes` rows. An automatic reseed
  on every deploy would therefore wipe **every leaderboard on every release**. Design:
  - `migrate` runs on **every** deploy (idempotent, additive).
  - **New `meta` table** (`key TEXT PRIMARY KEY, value TEXT`) created by `app.migrate` — it does not
    exist today (current tables: quizzes, questions, assets, contestants, attempts, answers, badges,
    issue_reports, duels).
  - Because deletion is **per quiz**, the hash is computed **per file**: `meta['content_sha:<slug>']`
    holds the SHA-256 of that quiz's JSON. On deploy, each quiz is reseeded **only if its own hash
    changed**. Editing `journals.json` therefore resets only the journals board; every other
    station's leaderboard is untouched.
  - A manual `workflow_dispatch: reseed` (optionally scoped to one slug) exists for forced reseeds.
  - Consequence, documented and intentional: changing a quiz's content resets **that quiz's** board.

## 6. Content packaging change

Today `content/` is both baked into the image (Dockerfile `COPY`) **and** bind-mounted over
(`./content:/srv/content`). On the server the bind mount is dropped and the baked copy is used.

- **Gain:** each release is one atomic artifact (code + content + assets); the server needs no repo
  checkout; the class of bug seen on 2026-07-28 (bind mount resolving to an empty dir) cannot occur.
- **Cost:** a content edit now requires a release. Correct behavior for a versioned, DOI-archived
  project.
- Local development keeps the bind mount via the existing `docker-compose.yml`.

## 7. Repository and release workflow

**Branches:** `master` → renamed **`main`**; new **`dev`** integration branch. Both protected:
no direct pushes, PR required, CI must pass.

**Flow:** issue → branch `feat/<issue#>-<slug>` → PR into `dev` → PR `dev` → `main` → GitHub Release
`vX.Y.Z` → automatic deploy + automatic Zenodo DOI.

**Scaffolding to add:**

| File | Purpose |
|------|---------|
| `LICENSE` | AGPL-3.0 |
| `README.md` | What it is, live link, architecture, dev setup, deploy, DOI badge |
| `CONTRIBUTING.md` | Branch/PR conventions, conventional commits, how to run tests |
| `SECURITY.md` | How to report a vulnerability (private advisory) |
| `CITATION.cff` | Author: Mulham Fetna, ORCID 0009-0006-4432-798X, `contact@mulhamfetna.com` |
| `.zenodo.json` | Zenodo metadata; DOI minted per release |
| `.github/ISSUE_TEMPLATE/{bug,feature,content-error}.yml` | Content-error template mirrors the in-app reporter |
| `.github/pull_request_template.md` | Checklist: tests, docs, conventional title |
| `.github/dependabot.yml` | pip + npm + GitHub Actions updates |

Semantic versioning; conventional commits drive an auto-generated changelog per release.

## 8. Workflows

**`ci.yml`** — on `pull_request` and `push` to `dev`/`main`, GitHub-hosted:
backend `pytest -q`, frontend `npm test` (Vitest). Required status check for both protected branches.

**`release.yml`** — on `release: published`:
1. *build* (GitHub-hosted): `docker/build-push-action` → `ghcr.io/mulhamfetna/boundless-src-researcher-journey-game:vX.Y.Z` and `:latest`, authenticated with the automatic `GITHUB_TOKEN`.
2. *deploy* (`runs-on: self-hosted`, `environment: production`, `needs: build`):
   `docker compose -f docker-compose.prod.yml pull` → `up -d` → `python -m app.migrate` →
   conditional seed (§5) → **smoke test** (`curl -f localhost:8000/api/quizzes` and one asset) →
   on failure, redeploy the previous tag and fail the job.

**`rollback.yml`** — `workflow_dispatch` with a `tag` input; self-hosted; pulls and starts that tag.

## 9. Secrets

`.env` (BOT_TOKEN, CLOUDFLARE_TUNNEL_TOKEN, ADMIN_ID, PUBLIC_URL) lives **only** on the server,
`chmod 600`, created once by hand. It is never committed, never uploaded to GitHub, and never
printed by a workflow. GHCR authentication uses the automatic `GITHUB_TOKEN`; **no additional
GitHub secrets are required.**

`BOT_TOKEN` must be **rotated** before the repo goes public — it appeared in an earlier chat
transcript. It has never been in git.

## 10. Excluded from the public repo

The six Arabic curriculum PDFs in the repo root are third-party course material and are added to
`.gitignore`. The repo ships only the derived, user-authored quiz content
(`content/questions/*.json`). `node_modules/`, `.env`, and `*.db` are already ignored.

## 11. Migration path (current state → target)

1. Rotate `BOT_TOKEN`; gitignore the PDFs.
2. Add scaffolding (§7) + workflows (§8) locally; rename `master`→`main`; create `dev`.
3. `gh repo create … --public --source=.` and push.
4. Configure branch protection, Environment `production`, labels.
5. Install the self-hosted runner on the server (non-root user, `docker` group, systemd service).
6. Create `/opt/researcher-journey/{docker-compose.prod.yml,.env}`; migrate the existing
   `quizdata` volume contents (copy `quiz.db` in) so leaderboards carry over.
7. Cut release `v1.0.0` → verify the image builds, deploys, and the smoke test passes.
8. Enable the Zenodo↔GitHub integration; the next release mints the DOI; add the badge.
9. Install the nightly backup timer.

## 12. Verification

- `ci.yml` green on a throwaway PR.
- A release deploys and the smoke test passes against `https://src.mulhamfetna.com`.
- `docker compose down && up -d` on the server preserves leaderboard rows (volume proof).
- A deploy with unchanged content leaves attempt counts intact (seed-skip proof).
- `rollback.yml` with the previous tag restores the prior version.
- Zenodo shows the release and returns a DOI.

## 13. Out of scope

- Staging/second environment.
- Migrating off SQLite.
- Automating the shared server's OS/network configuration beyond the runner service and backup timer.
