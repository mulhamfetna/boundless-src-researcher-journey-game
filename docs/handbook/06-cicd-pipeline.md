# 6 — The CI/CD pipeline

← [GitHub workflow](05-github-workflow.md) · [Index](README.md) · Next: [The server](07-the-server.md)

---

## Three workflows, two kinds of runner

```mermaid
flowchart TB
    subgraph gh["☁️ GitHub-hosted runners — disposable VMs"]
        CI["<b>ci.yml</b><br/>on: pull_request, push(main/dev)<br/>backend · frontend · content · workflow-security"]
        BUILD["<b>release.yml → build</b><br/>on: release published<br/>build + push to GHCR"]
    end
    subgraph self["🖥️ Self-hosted runner — YOUR server"]
        DEPLOY["<b>release.yml → deploy</b><br/>on: release published only"]
        ROLL["<b>rollback.yml</b><br/>on: workflow_dispatch only"]
    end

    BUILD -->|needs| DEPLOY

    style gh fill:#1e3a5f,color:#fff
    style self fill:#7c2d12,color:#fff
```

**The split is the security model.** Untrusted contributor code runs *only* on GitHub's throwaway
VMs. Your server runs only fixed scripts, triggered by events only a maintainer can cause.
Full reasoning in [Ch. 9](09-security-model.md).

---

## `ci.yml` — the gate on every pull request

```mermaid
flowchart LR
    PR["pull request"] --> P1["<b>backend</b><br/>pip install -e './backend[dev]'<br/>pytest -q → 141 tests"]
    PR --> P2["<b>frontend</b><br/>npm ci<br/>npm test → 54 tests"]
    PR --> P3["<b>content</b><br/>validate_quiz on all 7 files<br/>+ every question has a concept"]
    PR --> P4["<b>workflow-security</b><br/>no self-hosted job is<br/>reachable from a PR"]
    P1 & P2 & P3 & P4 --> G{"all green?"}
    G -->|yes| MERGE["merge allowed"]
    G -->|no| BLOCK["merge blocked"]

    style G fill:#b45309,color:#fff
    style BLOCK fill:#b91c1c,color:#fff
```

All four run **in parallel** on separate VMs — the slowest determines wall-clock time (~40s).

### The `workflow-security` job

This one guards the architecture itself. It parses every workflow file and fails if any job that
`runs-on: self-hosted` is reachable from `pull_request` or `pull_request_target`:

```python
selfhosted = [j for j, c in d.get("jobs", {}).items()
              if "self-hosted" in str(c.get("runs-on"))]
if selfhosted and {"pull_request", "pull_request_target"} & keys:
    bad.append((f, selfhosted))
```

**Why encode this as a test?** Because it is the single mistake that would turn a public repository
into remote code execution on a shared server. Documentation can be forgotten; a failing check
cannot.

---

## `release.yml` — build then deploy

```mermaid
sequenceDiagram
    autonumber
    actor M as Maintainer
    participant GH as GitHub
    participant VM as ubuntu-latest
    participant REG as ghcr.io
    participant R as self-hosted runner
    participant D as Docker on server

    M->>GH: publish release v1.0.1
    GH->>VM: start job "build"
    VM->>VM: checkout + setup buildx
    VM->>REG: login (auto GITHUB_TOKEN)
    VM->>VM: docker build (cached layers)
    VM->>REG: push :v1.0.1 and :latest
    VM-->>GH: build ✅

    GH-->>R: hand "deploy" down the open link
    R->>D: compose pull
    R->>D: compose up -d
    R->>D: python -m app.migrate
    R->>D: seed_changed()
    R->>R: smoke test 127.0.0.1:8000
    alt all good
        R->>R: mv .image-next .image-current
        R-->>GH: deploy ✅
    else any step failed
        R->>D: up -d with .image-current
        R-->>GH: deploy ❌ (rolled back)
    end
```

### The build job, line by line

| Step | What it does | The subtle part |
|---|---|---|
| `actions/checkout@v4` | clone the repo onto the VM | this is the Docker *build context* |
| `docker/setup-buildx-action@v3` | start BuildKit | required for the GHA layer cache |
| `docker/login-action@v3` | sign in to `ghcr.io` | uses `secrets.GITHUB_TOKEN` — **auto-minted, job-scoped, expires with the job.** You never created it |
| `docker/build-push-action@v6` | build + push | two tags, `cache-from/to: type=gha` |

**Why `permissions: packages: write` is declared:** the automatic token is read-only by default.
Declaring the minimum needed permission is what lets it push — and nothing more.

### Why the Dockerfile is ordered the way it is

```mermaid
flowchart TD
    L1["FROM python:3.12-slim"] --> L2["apt-get poppler-utils"]
    L2 --> L3["COPY backend/pyproject.toml <b>only</b>"]
    L3 --> L4["RUN pip install"]
    L4 --> L5["COPY backend/ frontend/ content/"]
    L5 --> L6["CMD uvicorn"]

    N1["rarely changes →<br/>cached almost forever"] -.-> L2
    N2["changes only when<br/>dependencies change"] -.-> L4
    N3["changes every release"] -.-> L5

    style L4 fill:#0f766e,color:#fff
    style L5 fill:#b45309,color:#fff
```

Copying `pyproject.toml` **alone** before the source is the whole trick: Docker caches layers in
order, so editing `api.py` invalidates only the last `COPY`. Dependencies are not reinstalled.
Copy the source first and every build reinstalls everything.

### The deploy job, step by step

```mermaid
flowchart TD
    S1["<b>1. Record intent</b><br/>echo image > .image-next"] --> S2
    S2["<b>2. Pull and start</b><br/>compose pull && up -d"] --> S3
    S3["<b>3. Migrate</b><br/>idempotent, safe every time"] --> S4
    S4["<b>4. Seed only changed</b><br/>seed_changed()"] --> S5
    S5["<b>5. Smoke test</b><br/>poll /api/quizzes ×15,<br/>then fetch a real asset"] --> OK{"?"}
    OK -->|pass| S7["<b>7. Record success</b><br/>mv .image-next .image-current"]
    OK -->|fail| S6["<b>6. Roll back</b><br/>up -d with .image-current"]

    style S5 fill:#b45309,color:#fff
    style S6 fill:#b91c1c,color:#fff
    style S7 fill:#0f766e,color:#fff
```

**Why `up -d` and not `restart`:** `restart` reuses existing containers with the *old* image.
`up -d` compares desired against actual state, sees a new image tag, and recreates only what
changed — `cloudflared` is untouched, so **the tunnel never drops during a deploy.**

**Why the smoke test polls:** the container needs a second or two to bind. Fifteen attempts two
seconds apart tolerates a slow start without hanging forever.

**Why it also fetches an asset:** an API-only check would have passed during the 2026-07-28 outage,
when every image 404'd. Checking a real asset catches a broken content mount.

**Why `.image-current` matters:** it is the memory that makes rollback possible. Written only
*after* a successful smoke test, so it always names a version known to work.

⚠️ **Both files must be named explicitly:**
```yaml
COMPOSE_FILES: "-f docker-compose.prod.yml -f docker-compose.override.yml"
```
Passing an explicit `-f` **disables Compose's automatic loading** of `docker-compose.override.yml`.
Miss this and the container is recreated without the loopback port, and the smoke test can never
pass. This cost a failed deploy — see [Ch. 11](11-incidents.md).

---

## `rollback.yml` — the recovery path

```mermaid
flowchart LR
    OPS["Actions tab →<br/>Rollback → tag v1.0.0"] --> R["self-hosted runner"]
    R --> P["compose pull that tag"]
    P --> U["up -d"]
    U --> SM["smoke test"]
    SM --> REC["record .image-current"]

    style OPS fill:#7c3aed,color:#fff
```

Rollback is trivial **because images are immutable**. `v1.0.0` will always be the identical bytes,
however many releases follow. Recovery is a pull, not a rebuild — no dependency has drifted, no
base image has moved.

## What the pipeline costs

| Stage | Time |
|---|---|
| CI (4 parallel jobs) | ~40 s |
| Image build (cached) | ~1–2 min |
| Deploy on the server | **19 s** (measured, v1.0.1) |

---

Next: [The server](07-the-server.md).
