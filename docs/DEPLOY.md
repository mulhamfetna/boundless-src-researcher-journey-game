# Deploy

## Prerequisites
- A bot token from @BotFather.
- An HTTPS domain pointing at the host (Telegram Mini Apps require HTTPS).

## Steps
1. `cp .env.example .env` and fill `BOT_TOKEN` + `PUBLIC_URL` (the public HTTPS URL).
2. Seed the database once:
   `docker compose run --rm web python -c "import sys; sys.path.insert(0,'.'); from app.db import connect, init_schema; from app.seed import seed_from_file; c=connect('/data/quiz.db'); init_schema(c); seed_from_file(c,'/srv/content/questions/journals.json')"`
3. `docker compose up -d --build`.
4. Put a TLS-terminating reverse proxy (your existing setup) in front of `web:8000` for `PUBLIC_URL`.
5. In @BotFather: set the Mini App / menu button URL to `PUBLIC_URL/app/`.
6. Open the bot, press **/start**, then the **ابدأ المسابقة** button.

## Notes
- The bot uses long polling (no inbound webhook needed). Only the Mini App needs the public HTTPS URL.
- Scores persist in the `quizdata` volume.
