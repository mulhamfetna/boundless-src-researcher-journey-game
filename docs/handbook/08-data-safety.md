# 8 — Data safety

← [The server](07-the-server.md) · [Index](README.md) · Next: [Security model](09-security-model.md)

---

Everything a learner earns — attempts, scores, badges, duels — lives in **one SQLite file**. This
chapter is how that file survives deployments, container replacement, reboots, and mistakes.

## The three layers

```mermaid
flowchart TB
    L1["<b>1. Named volume</b><br/>survives container replacement"]
    L2["<b>2. Content hashing</b><br/>survives deployments"]
    L3["<b>3. Nightly verified backups</b><br/>survives everything else"]
    L1 --> L2 --> L3

    style L1 fill:#0f766e,color:#fff
    style L2 fill:#b45309,color:#fff
    style L3 fill:#7c3aed,color:#fff
```

---

## Layer 1 — the named volume

```mermaid
flowchart LR
    subgraph host["Docker's storage"]
        V[("researcher-journey_quizdata<br/>quiz.db")]
    end
    C1["web container<br/>(v1.0.0)"] -.->|destroyed on deploy| X["🗑️"]
    C2["web container<br/>(v1.0.1)"] --> V
    C1 --> V

    style V fill:#7c3aed,color:#fff
```

The volume is **independent of any container**. Deploys destroy and recreate containers; the volume
is simply re-attached.

| Operation | Data |
|---|---|
| `docker compose up -d` (new image) | ✅ survives |
| `docker compose down` then `up` | ✅ survives |
| `docker rm`, image deletion, reboot | ✅ survives |
| ⚠️ `docker compose down **-v**` | ❌ **destroyed** |
| `docker volume rm …` | ❌ destroyed |

**Why a named volume and not a bind mount?** A bind mount depends on a host path resolving
correctly at container start. On 2026-07-28 exactly that failed on the laptop — a late-mounting
disk meant Docker bound an empty directory and every asset 404'd. A named volume has no host-path
dependency and cannot fail that way.

---

## Layer 2 — content hashing (deploy safety)

### The hazard

```mermaid
flowchart LR
    S["seed_quiz(slug)"] --> D1["DELETE answers"] --> D2["DELETE attempts"] --> D3["DELETE questions"] --> I["INSERT fresh"]
    D2 -.->|"⚠️ the leaderboard<br/>for that station"| GONE["gone"]

    style GONE fill:#b91c1c,color:#fff
```

Seeding is destructive by design — it guarantees the database matches the file. But an automated
deploy that seeds unconditionally would **wipe every leaderboard on every release**.

### The mechanism

```mermaid
flowchart TD
    F["for each content/questions/*.json"] --> H["sha256(file)"]
    H --> CMP{"compare with<br/>meta['content_sha:slug']"}
    CMP -->|equal| SKIP["<b>skipped</b><br/>nothing touched"]
    CMP -->|different| SEED["<b>seeded</b><br/>reseed — attempts reset"]
    CMP -->|"no hash stored<br/>AND quiz exists"| ADOPT["<b>adopted</b><br/>record the hash,<br/>change nothing"]
    CMP -->|"no hash stored<br/>AND quiz is new"| SEED

    style SKIP fill:#0f766e,color:#fff
    style ADOPT fill:#7c3aed,color:#fff
    style SEED fill:#b45309,color:#fff
```

Hashing is **per file**, so editing `journals.json` resets only the journals board; the other six
stations are untouched.

### Why "adopt" exists

This third outcome was added after a real incident. A database created *before* hashing existed has
quiz rows but no `content_sha`. Treating "no hash" as "changed" reseeded all seven stations and
**deleted every attempt** ([Ch. 11](11-incidents.md)).

The reasoning behind the fix is worth stating explicitly, because it generalises:

> **The risks are asymmetric. Data loss is irreversible; stale content is not.**
> When you cannot tell whether content changed, choose the recoverable mistake.

An adopted quiz records its hash, so any *genuine* later edit changes the hash and seeds normally.
`force=True` still reseeds deliberately.

Verified in production on v1.0.1:
```
{'seeded': [], 'skipped': ['capstone','foundations','journals',
                           'paper-parts','paper-types','publishing','submission'], 'adopted': []}
```

---

## Layer 3 — nightly backups

```mermaid
flowchart LR
    CRON["cron 03:30<br/><i>dev's crontab</i>"] --> SH["backup.sh"]
    SH --> C["throwaway container<br/>--user dev, source :ro"]
    C --> BK["sqlite3.backup()<br/>→ backups/quiz-YYYY-MM-DD.db"]
    BK --> VER["verify integrity_check<br/>+ count attempts"]
    VER --> PRUNE["delete older than 14 days"]

    style VER fill:#0f766e,color:#fff
```

Every choice in that script answers a real problem:

| Choice | Why |
|---|---|
| Runs in a container | the DB is inside a Docker volume; the host has no `sqlite3` |
| `sqlite3.backup()` not `cp` | copying a live SQLite file can capture a **torn, unusable** file |
| Python's binding, not the CLI | the app image is `python:3.12-slim` — **it ships no `sqlite3` binary** |
| `--user $(id -u):$(id -g)` | otherwise backups are root-owned and `dev` can neither read nor prune them |
| source mounted `:ro` | a backup can never modify production |
| verifies after writing | **an unverified backup is not a backup** |
| reads `.image-current` | always uses the image actually deployed |
| **03:30**, not 03:00 | `dev` already has a 03:00 job — the crontab was *appended to*, never rewritten |

---

## The restore drill

Producing backups proves nothing. **Restoring one does.**

```mermaid
flowchart LR
    B["backups/quiz-2026-08-02.db"] --> SV["scratch volume<br/><i>restore-drill</i>"]
    SV --> CHK["integrity_check: ok<br/>attempts: 2<br/>leaderboard: محمد 459"]
    CHK --> RM["scratch volume deleted"]
    PROD[("production volume")] -.->|untouched| PROD

    style CHK fill:#0f766e,color:#fff
```

Run non-destructively, against a scratch volume, with production untouched throughout.

### Restore runbook

```bash
cd ~/mulham/src
IMAGE=$(cat .image-current)
C="-f docker-compose.prod.yml -f docker-compose.override.yml"

# 1. INSPECT first — never restore a backup you haven't opened
docker volume create restore-drill
docker run --rm -v restore-drill:/data -v ~/mulham/src/backups:/bk:ro alpine:3 \
  sh -c "cp /bk/quiz-YYYY-MM-DD.db /data/quiz.db"
docker run --rm -v restore-drill:/data "$IMAGE" python -c \
  "import sqlite3;c=sqlite3.connect('/data/quiz.db');\
print(c.execute('PRAGMA integrity_check').fetchone()[0],\
c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0])"
docker volume rm restore-drill

# 2. Only once satisfied, restore for real
docker compose $C down                 # ⚠️ never -v
docker run --rm -v researcher-journey_quizdata:/data -v ~/mulham/src/backups:/bk:ro alpine:3 \
  sh -c "cp /bk/quiz-YYYY-MM-DD.db /data/quiz.db && chmod 644 /data/quiz.db"
docker compose $C up -d
```

> **Gotcha found during the real drill:** do **not** pass `--user` when copying into a *fresh*
> volume — it is root-owned until something writes to it, and the copy fails with
> `Permission denied`.

---

## Migrating a database between machines

```mermaid
sequenceDiagram
    participant L as Laptop
    participant S as Server
    Note over L: stop the stack FIRST — halts writes
    L->>L: sqlite3.backup() → export.db
    L->>S: rsync
    S->>S: copy into the volume via alpine
    S->>S: verify row counts match
    Note over S: ⚠️ stamp content hashes BEFORE seeding
```

⚠️ **That last step is the one that was missed**, and it caused the incident. A database adopted
from elsewhere arrives with **no `content_sha` rows**, so the first `seed_changed` had no baseline.
The `adopt` behaviour now handles this automatically — but when moving data by hand, stamp the
hashes first.

---

Next: [The security model](09-security-model.md).
