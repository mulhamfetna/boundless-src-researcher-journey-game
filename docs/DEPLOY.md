# Deploy — Go Live via Cloudflare Tunnel

This runs the whole stack with Docker Compose and exposes the Mini App on a
subdomain of your Cloudflare domain over HTTPS — **no open ports, no TLS certs
to manage**. Cloudflare creates the DNS record and the certificate for you.

```
Telegram  ──HTTPS──>  quiz.your-domain.com  ──Cloudflare edge──>  cloudflared
                                                                      │ (encrypted tunnel)
                                                                      ▼
                                                              web:8000 (FastAPI + Mini App)
```

## Prerequisites

- Your domain is already added to Cloudflare (it is — you have a Cloudflare domain).
- A bot token from **@BotFather** (already in `.env`).
- Docker + Docker Compose on the host (verified: Docker 29, Compose v2).

---

## Step 1 — Create the tunnel in the Cloudflare dashboard

1. Go to the **Zero Trust** dashboard: <https://one.dash.cloudflare.com> →
   pick your account.
2. Left sidebar: **Networks → Tunnels** → **Create a tunnel**.
3. Connector type: **Cloudflared** → **Next**.
4. Name it `gamified-quiz` → **Save tunnel**.
5. The next screen ("Install and run a connector") shows a command containing a
   long token: `cloudflared ... run --token eyJhbGciOi....`
   **Copy only the token** (the `eyJ...` string). You do **not** run their
   command — our `cloudflared` compose service runs it for you.
6. Leave this wizard open and go to **Step 2**; you'll come back for Step 3.

## Step 2 — Put the token + subdomain into `.env`

On the host, in the project root:

```bash
cp .env.example .env   # if you don't already have a .env
```

Edit `.env` and set these values (keep your existing `BOT_TOKEN`):

```bash
BOT_TOKEN=<your real BotFather token>
PUBLIC_URL=https://quiz.your-domain.com          # <- your chosen subdomain
CLOUDFLARE_TUNNEL_TOKEN=eyJ...                    # <- token from Step 1
QUIZ_DB_PATH=/data/quiz.db
```

Use the **same** subdomain in `PUBLIC_URL` here and in Step 3 and Step 6.

## Step 3 — Add the public hostname (this creates DNS + TLS automatically)

Back in the tunnel wizard (or **Networks → Tunnels → gamified-quiz →
Public Hostname → Add a public hostname**):

| Field | Value |
|-------|-------|
| **Subdomain** | `quiz` |
| **Domain** | `your-domain.com` (pick from the dropdown) |
| **Path** | *(leave blank)* |
| **Service → Type** | `HTTP` |
| **Service → URL** | `web:8000` |

Click **Save hostname**.

What this does for you automatically:
- **DNS:** creates a proxied `CNAME` record `quiz → <tunnel-id>.cfargotunnel.com`
  (orange cloud). You don't touch the DNS app.
- **TLS:** Cloudflare's Universal SSL certificate already covers
  `quiz.your-domain.com` (a first-level subdomain), so HTTPS works with no cert
  steps. The hop from Cloudflare to your container is encrypted inside the tunnel.

> Service URL is `web:8000` (not `localhost`) because cloudflared and web run in
> the same compose network and reach each other by service name. It's `HTTP`,
> not HTTPS, because Cloudflare terminates TLS at its edge.

## Step 4 — Bring the stack up

```bash
docker compose up -d --build
```

This starts three services: `web` (API + Mini App), `bot` (Telegram), and
`cloudflared` (the tunnel). Confirm the tunnel is connected:

```bash
docker compose logs cloudflared | grep -i "registered\|connection"
```

In the dashboard the tunnel status should flip to **Healthy**.

## Step 5 — Seed the quiz database (one time)

The DB lives in the `quizdata` volume and starts empty. Load the journals quiz:

```bash
docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_from_file; c=connect('/data/quiz.db'); init_schema(c); print('seeded quiz', seed_from_file(c,'/srv/content/questions/journals.json'))"
```

Expected: `seeded quiz 1`. **To load all quizzes at once** (recommended once you
have multiple), use `seed_all` instead of `seed_from_file`:

```bash
docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect; from app.seed import seed_all; c=connect('/data/quiz.db'); print('seeded', seed_all(c, '/srv/content/questions'))"
```

Verify through the tunnel:

```bash
curl -s https://quiz.your-domain.com/api/quizzes
# -> all quiz slugs, e.g. journals, foundations, paper-types, paper-parts
```

## Step 6 — Point the bot's Mini App at the URL (BotFather)

In Telegram, talk to **@BotFather**:

1. `/mybots` → select your bot → **Bot Settings** → **Menu Button** →
   **Edit menu button URL** → send `https://quiz.your-domain.com/app/`
   (note the trailing `/app/`).
2. (Optional) `/setmenubuttontext` → e.g. `ابدأ المسابقة`.

The bot's own `/start` button also opens this same URL (already coded in
`app/bot.py` from `PUBLIC_URL`).

## Step 7 — Go live & smoke test

- Open your bot in Telegram → **/start** → tap **ابدأ المسابقة 🎮**.
- The RTL Mini App opens; play the journals quiz; finish to see the report
  with the real source screenshots.
- Send **/leaderboard** in the chat — your score should appear.

---

## Operations notes

- **Only one bot process per token.** Don't run `bot` here *and* on another host
  with the same `BOT_TOKEN` — Telegram long-polling allows a single consumer.
  When you migrate hosts, `docker compose down` here first.
- **Data lives in the `quizdata` volume.** To move servers, migrate that volume
  (`docker run --rm -v quizdata:/d -v $PWD:/b busybox tar czf /b/quizdata.tgz -C /d .`)
  or you'll start with an empty leaderboard.
- **Lock it down (optional):** once the tunnel works, delete the `ports:` block
  from the `web` service so the app is reachable *only* through Cloudflare.
- **Re-seed / update questions:** edit `content/questions/journals.json`, then
  re-run the Step 5 command. **Re-seeding replaces the quiz and clears that
  quiz's attempts/answers** (a content reset) — the leaderboard for it starts
  fresh. Badges are contestant-scoped and are NOT cleared by re-seeding. Only re-seed when you intend to reset play data for that quiz.
- **Logs:** `docker compose logs -f web bot cloudflared`.

## Upgrades (pulling new code)

After pulling new code that changes the backend or schema:

```bash
docker compose build web bot
docker compose run --rm web python -m app.migrate   # idempotent; prints changes or "already current"
# re-seed only if content changed (this resets that quiz's play data):
docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect; from app.seed import seed_from_file; c=connect('/data/quiz.db'); print('seeded', seed_from_file(c,'/srv/content/questions/journals.json'))"
docker compose up -d web bot cloudflared
```

`app.migrate` is safe to run repeatedly — it adds the `max_streak` column,
drops the legacy question-type CHECK, and ensures the `badges` table +
`UNIQUE(contestant_id, code)` exist, skipping whatever is already current.

## ⚠️ Frontend cache — bump the asset version on every frontend deploy

Cloudflare edge-caches static assets (`app.js`, `styles.css`) for hours. After a
frontend change, the container serves the new file but Cloudflare keeps serving
the **old** one — and a fresh `index.html` (Cloudflare returns HTML as `DYNAMIC`,
uncached) running an old `app.js` breaks the app.

**Fix in place — fully automatic, nothing to remember:** `main.py` serves
`index.html` through a dynamic `/app/` route that stamps the `app.js`/`styles.css`
URLs with `?v=<hash>`, where `<hash>` is an 8-char SHA of the current bundle.
Change either file → the hash changes → the URL changes → guaranteed Cloudflare
cache miss → users get the new bundle on next load, **no purge, no manual bump**.
`main.py` also sends `Cache-Control: no-cache` for `/app/*` (edge revalidates via
etag). `index.html` is `DYNAMIC` (never edge-cached), so the fresh hash always
reaches the client.

Verify after any frontend deploy:
```bash
VER=$(curl -s "https://src.mulhamfetna.com/app/" | grep -oE "app\.js\?v=[a-z0-9]+" | head -1 | cut -d= -f2)
diff <(curl -s "https://src.mulhamfetna.com/app/app.js?v=$VER") frontend/app.js && echo "fresh"
```
