# Server setup — what, how, when, why

Living record of the production deployment on the shared server `amd`. Every decision below
records **why** it was made, not just what was done, so the setup can be audited, repeated, or
reversed by someone who wasn't here.

**Status:** **LIVE on the server** since 2026-07-29. The laptop stack is stopped. See the
incident in §10 — the first deploy lost data and it was recovered.

**Install location:** `/home/dev/mulham/src` — chosen by the owner so everything this project adds
lives under one directory instead of being scattered across a shared machine. Removing that one
directory (plus one Docker volume) removes the entire deployment.

---

## 0. The machine (surveyed 2026-07-29, read-only)

| Fact | Value | Why it matters |
|---|---|---|
| OS | Ubuntu 24.04.4 LTS | Modern systemd; the official GitHub runner supports it |
| Arch | `x86_64` | Same as the CI builder — **no ARM cross-build needed** |
| CPU / RAM | 32 cores / 123 GB (117 GB free) | Our stack needs a fraction of this |
| Disk | 937 GB, 494 GB free (45 % used) | Images and backups are negligible here |
| Uptime | 17 days | Stable; but see the reboot risk in §6 |
| Docker | 29.6.2, Compose v5.3.1 | Both present — nothing to install |
| User | `dev` (uid 1000), in `docker` **and** `sudo` | Can run containers without sudo |
| Passwordless sudo | **No** — sudo prompts for a password | Shapes the whole design (§2) |

### What else lives here (this box is busy)

21 running containers, none of them ours: a Postgres (`wsh-pg`, loopback only), SearxNG (`:8081`),
about ten Squid proxies (`:33333–:44448`), and a fleet of Redroid Android containers.

> **Note, not a task:** many `redroid*` containers are in `Restarting (129)` crash-loops. That is
> pre-existing and unrelated to this project. **We do not touch them.** Flagging it only so nobody
> later blames this deployment for the noise in `docker ps`.

### Collision check — everything we need is free

| Resource we want | Status |
|---|---|
| TCP port 8000 | **free** (0 listeners) |
| Volume `*quiz*` / `*research*` | none exist |
| Containers `web` / `bot` / `cloudflared` | none exist |
| `/opt/researcher-journey` | does not exist |
| Existing GitHub Actions runner | none |
| `cloudflared` (host binary or container) | none |

**Conclusion:** we can deploy without disturbing a single running service.

---

## 1. Why pull-based deployment (and not SSH-from-CI)

**What:** a GitHub Actions *self-hosted runner* runs on the server. It opens an **outbound** HTTPS
connection to GitHub and waits for jobs.

**Why not the obvious alternative?** The common pattern is "GitHub SSHes into the server and runs a
deploy script". That requires the server to accept inbound connections from GitHub's IP ranges and
a private key stored in GitHub secrets. On a **shared** box, that means changing firewall/network
policy that other services depend on, and creating a credential that, if leaked, grants shell
access. Rejected.

**Why this is safe here:** nothing listens for GitHub. The runner dials out, exactly like a browser.
No port opened, no firewall rule, no inbound exposure, no SSH key in GitHub.

**When it runs:** only when a **release is published** (or a rollback is dispatched by hand). Never
on a pull request — see §5.

---

## 2. Why we avoid `sudo` almost entirely

**The constraint:** `sudo` on this box prompts for a password. A non-interactive SSH session cannot
answer that prompt, and piping a password into `sudo -S` would put the secret into a command line
(visible in the process table and in logs). **Unacceptable.**

**The consequence — two deliberate deviations from the original plan:**

| Original plan | What we do instead | Why |
|---|---|---|
| Create a dedicated `deploy` user | Run as the existing `dev` user | Creating a user needs sudo. `dev` already has docker access, and is the only human account on the box. |
| Install into `/opt/researcher-journey` | Install into `/home/dev/mulham/src` | Writing to `/opt` needs sudo; a home directory is equally durable. The owner also wants everything under one directory rather than scattered across a shared machine. |
| `systemd` **system** service for backups | A **user `cron`** entry | `crontab -e` needs no sudo. |

### Why `COMPOSE_PROJECT_NAME` is set explicitly

Compose derives the project name from the directory, which here would be `src` — producing
`src-web-1` on a host already running 21 unrelated containers. `COMPOSE_PROJECT_NAME=researcher-journey`
(set in `.env`) makes every container and the volume unmistakably ours, so nobody later has to guess
what `src-web-1` was, and so a stray `docker compose down` in another directory cannot match ours.

### Why the server `.env` is smaller than the laptop's

Only `BOT_TOKEN`, `PUBLIC_URL`, `CLOUDFLARE_TUNNEL_TOKEN`, `ADMIN_ID` (plus the two non-secret
compose settings) are copied. `GEMINI_API_KEY` and `GEMINI_PROJECT` are **deliberately excluded** —
they serve local art generation only. Least privilege: a shared machine should not hold a credential
it has no use for.

**The one place sudo was unavoidable:** `./svc.sh install dev`, which writes a unit file to
`/etc/systemd/system/`. This is what makes the runner start automatically after a reboot — without
it the runner would die at logout and deployments would silently stop working.

**How the password was handled:** written to a `600` file, transferred with `rsync`, fed to
`sudo -S` via stdin redirection, then **shredded on both machines** immediately afterwards. It was
never placed on a command line, so it never appeared in the process table or shell history. The
same pattern was used for the runner registration token.

---

## 3. Why the server holds no source code

The server gets only three things:

```
/home/dev/mulham/src/
  docker-compose.prod.yml      # which image to run, and how          (644)
  docker-compose.override.yml  # binds 127.0.0.1:8000 for the smoke test (644)
  .env                         # secrets                               (600)
  └ docker volume "researcher-journey_quizdata"  → /data/quiz.db
```

**Why no `git clone`?** Because then "what is deployed" becomes "whatever the working tree happens
to contain" — untracked edits, half-finished merges, a forgotten `git stash`. Instead the unit of
deployment is an **immutable, versioned image** (`ghcr.io/…:v1.2.3`). What ran yesterday can be
reproduced exactly. Rollback is pulling an older tag, not reverse-engineering a directory.

**Why is content baked into the image?** Because content *is* part of the release. On 2026-07-28 a
bind-mounted content directory silently resolved to an empty folder after a reboot and every image
404'd. Baking it in makes that failure impossible and makes each release a single citable artifact.
The cost — a content fix needs a release — is accepted deliberately.

---

## 4. The database: why it survives everything

**What:** a Docker **named volume**, mounted at `/data`, holding `quiz.db`.

**Why a named volume and not a bind mount?** A bind mount depends on a host path existing and
resolving correctly at container start — exactly the failure that broke the app on 2026-07-28. A
named volume is managed by Docker, has no host-path dependency, and is untouched by
`docker compose down`, `up`, `pull`, image replacement, or container deletion.

**When could data be lost?** Only three ways, all deliberate:
1. `docker compose down -v` — the `-v` deletes volumes. **Never run this.**
2. `docker volume rm` — explicit.
3. Disk failure — which is why §7 adds nightly backups.

**Why `.backup` and not `cp`?** Copying a SQLite file while a process is writing can capture a torn,
unrecoverable file. The online-backup API is safe against a live writer.

**Implementation note:** the app image is `python:3.12-slim` and does **not** ship the `sqlite3`
CLI, so the backup is taken with Python's `sqlite3.Connection.backup()` — the same online-backup
API, always available because the app already depends on the module.

---

## 5. Why a public repo + self-hosted runner is still safe

GitHub warns against self-hosted runners on public repositories: normally, anyone can open a pull
request whose workflow code then executes on your machine. On a shared server that would be severe.

**How it is neutralised — trust is split by event:**

| Job | Runs where | Triggered by | Executes contributor code? |
|---|---|---|---|
| `backend`, `frontend`, `content`, `workflow-security` | GitHub's disposable runners | `pull_request` | Yes — safely, in GitHub's sandbox |
| `build` | GitHub's runners | `release: published` | No |
| `deploy` | **this server** | `release: published` **only** | No — fixed script |

A fork's pull request can never reach the server: the only workflow that touches it is gated to
`release: published`, an event only a maintainer can trigger. The `workflow-security` CI job
mechanically re-checks this on every pull request, so the guarantee cannot be lost by accident.

---

## 6. The Cloudflare tunnel cut-over (the one genuinely risky step)

**The hazard:** the tunnel token identifies a *connector*. If the laptop and the server both run
`cloudflared` with the **same token**, Cloudflare sees two healthy connectors for one tunnel and
**load-balances between them**. Users would randomly hit the laptop or the server — the same URL
serving two different databases, with attempts landing in whichever machine answered.

**Therefore:** the laptop stack must be stopped **before** the server's `cloudflared` starts, and
the cut-over is a single deliberate step, never an accident.

**Reboot risk:** all our containers use `restart: unless-stopped`, so they return automatically
after a reboot. Unlike the laptop, `/home/dev/mulham/src` lives on the root filesystem, so the
late-mount race that caused the 2026-07-28 outage **cannot occur here**.

---

## 7. Planned iterations

Each is applied only after explicit approval, and each is independently reversible.

| # | Step | Risk | Undo | Status |
|---|---|---|---|---|
| 1 | Create `~/mulham/src`, compose files, `.env` | none — writes files only | `rm -rf ~/mulham/src` | **done** |
| 2 | Create the volume and load `quiz.db` into it | none — nothing runs; laptop keeps serving | `docker volume rm researcher-journey_quizdata` | **done** |
| 3 | Install the GitHub runner | low | `./config.sh remove` | **done** |
| 4 | **Cut traffic over**: stop the laptop, publish `v1.0.0` → build + deploy + tunnel | **highest** | rollback workflow, or restart the laptop stack | **done** (see §10) |
| 5 | Nightly backup cron | none | `crontab -r` | next |
| 6 | Zenodo DOI + badge | none | — | |

### A sequencing constraint worth understanding

The image `ghcr.io/…:latest` **does not exist yet** — it is built by the release workflow, so there
is nothing to pull until the first release. That forces the order above:

1. the **database must be in place first** (step 2), because the deploy starts serving immediately;
2. the **runner must exist** (step 3), or the release's deploy job has nowhere to run;
3. only then the release (step 4), which builds, deploys, and starts the tunnel in one go.

Because `docker compose up -d` starts **every** service including `cloudflared`, the first deploy is
also the traffic cut-over. The laptop stack must therefore be stopped immediately before publishing
the release (see §6), which means a **short outage** — roughly the image build time (2–4 minutes).
This is accepted deliberately: the alternative, two live connectors, would split users across two
diverging databases, which is far worse than a few minutes offline.

---

## 8. Credential hygiene

- The server password was pasted into a chat transcript. **Rotate it.** All access here uses the
  SSH key `amd-trading`; the password is never used, stored, or written to any file.
- `BOT_TOKEN` also appeared in a transcript. It has never been in git, so publishing the repo did
  not leak it — but rotate it via `@BotFather` regardless.
- `.env` on the server is `chmod 600` (readable only by `dev`) and is never printed by a workflow.
- GitHub needs **no** secrets beyond the automatic `GITHUB_TOKEN`: GHCR authentication is built in.

---

## 9. Change log

| Date | Change | By |
|---|---|---|
| 2026-07-29 | Read-only survey; no changes made | Claude |
| 2026-07-29 | **Iteration 3**: installed GitHub runner `amd-shared` v2.336.0 into `~/mulham/src/actions-runner`, registered with a short-lived token (file-passed, then shredded), installed as systemd service `actions.runner.…amd-shared` (enabled at boot, runs as `dev`). GitHub reports **online**. Installer tarball deleted. | Claude |
| 2026-07-29 | **Iteration 2**: created volume `researcher-journey_quizdata` and loaded `quiz.db` via `sqlite3.backup()`. Verified all 8 tables match the laptop exactly (6 contestants / 2 attempts / 14 answers / 8 badges / 7 quizzes / 60 questions / 1 duel), `integrity_check: ok`. Transfer copies deleted from both machines. | Claude |
| 2026-07-29 | **Iteration 1**: created `/home/dev/mulham/src`; rsynced `docker-compose.prod.yml`, `docker-compose.override.yml` (127.0.0.1 only), and a minimal `.env` (`chmod 600`, Gemini keys excluded). Nothing started. | Claude |


---

## 10. Incident: the first deploy deleted every attempt (2026-07-29)

**Impact:** all `attempts` (2) and `answers` (14) were deleted; the public leaderboard went empty
for roughly four minutes. Contestants and badges were untouched. **Fully recovered** — no permanent
data loss.

**Timeline (UTC)**

| Time | Event |
|---|---|
| 12:17:53 | Laptop stack stopped (`down`, no `-v`). Planned downtime begins. |
| 12:18:30 | Release `v1.0.0` published. Image build starts. |
| 12:19:39 | Build **succeeded**; deploy job **failed on its first step**. |
| ~12:20:30 | Deployed manually from the built image — site back up (≈2.5 min downtime). |
| ~12:21 | Post-deploy check: `attempts 2 → 0`. Leaderboard empty. |
| ~12:23 | Restored from the laptop volume; content hashes stamped; verified. |

### Cause 1 — the deploy job never ran

`release.yml` had `DIR: /opt/researcher-journey` hard-coded. The install had been moved to
`/home/dev/mulham/src` at the owner's request and the workflow was never updated, so the job failed
at `cd "$DIR"`. A second latent bug was found while fixing it: every compose call passed only
`-f docker-compose.prod.yml`, and an explicit `-f` **disables** Compose's automatic loading of
`docker-compose.override.yml`. The container would have been recreated without the `127.0.0.1:8000`
publish, so the smoke test could never have passed even after the path was fixed.

### Cause 2 — the data loss (the important one)

`seed_changed` decides whether to reseed by comparing a stored `content_sha:<slug>` against the
file's hash. The database copied from the laptop predated that mechanism: it had quiz rows but
**no stored hashes**. "No hash" was treated as "changed", so all seven stations were reseeded — and
`seed_quiz` deletes a quiz's answers and attempts before reinserting.

The irony is exact: the feature written to stop deploys wiping leaderboards wiped the leaderboard,
because its very first run had nothing to compare against.

### Fix

`seed_changed` now distinguishes a third case, **adopt**: if a quiz already exists but has no stored
hash, its provenance is unknown, so the hash is recorded and *the data is left alone*. The
reasoning is asymmetric risk — **data loss is irreversible, stale content is not.** Any genuine
later edit changes the hash and seeds normally; `force=True` still reseeds deliberately.

Covered by `backend/tests/test_seed_changed.py::test_adopts_an_existing_quiz_that_has_no_stored_hash`.

### What this cost, and what saved it

Recovery was possible only because `docker compose down` was used instead of `down -v`, so the
laptop volume still held the original database. **That single character was the whole backup.**
This is why §7's nightly backup is no longer optional.

### Lessons applied

1. A path referenced by automation must be asserted, not assumed — the deploy now fails loudly at
   a wrong path rather than silently at the wrong moment.
2. Any migration that adopts an existing database must **bootstrap its own metadata first**, or the
   first run of a "safe" check runs with no baseline.
3. Verify data counts *after* a deploy, not only service health. The site returned `200` while the
   leaderboard was empty.
