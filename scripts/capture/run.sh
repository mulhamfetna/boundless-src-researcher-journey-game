#!/usr/bin/env bash
# Capture screenshots and clips from the real app, reproducibly.
#
# Starts a throwaway backend on a throwaway database, seeds it from the content
# in this working tree, drives the Mini App in Chrome, and tears everything down
# again. Nothing touches the production database or the deployed site.
#
# The bot token is fake on purpose: it is only ever used to HMAC-sign the demo
# player's initData so backend/app/auth.py accepts it. Both ends use the same
# fake token, so the signature verifies and no real credential is involved.
#
#   scripts/capture/run.sh --probe
#   scripts/capture/run.sh --scene map
#   scripts/capture/run.sh --scene all
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${CAPTURE_PORT:-8077}"
WORK="$(mktemp -d)"
DB="$WORK/capture.db"
export CAPTURE_BOT_TOKEN="${CAPTURE_BOT_TOKEN:-1234567:CAPTURE-DEV-TOKEN-NOT-REAL}"
export CAPTURE_BASE_URL="http://127.0.0.1:$PORT"

cleanup() {
  [[ -n "${SERVER_PID:-}" ]] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

echo "==> seeding a throwaway database"
( cd "$REPO/backend" && QUIZ_DB_PATH="$DB" python3 -c "
import os, sys; sys.path.insert(0, '.')
from app.db import connect, init_schema
from app.seed import seed_all
c = connect(os.environ['QUIZ_DB_PATH']); init_schema(c)
print('   stations:', ', '.join(seed_all(c, '../content/questions')))
" )

# Refuse to adopt a server we did not start. Without this the readiness probe
# below is happily satisfied by whatever is already on the port — which once
# meant capturing against a stale server holding a different database, and the
# only symptom was an HTTP 500 deep inside a take.
if curl -fsS -o /dev/null --max-time 2 "$CAPTURE_BASE_URL/api/quizzes" 2>/dev/null; then
  echo "port $PORT is already serving something. Stop it first, or set CAPTURE_PORT." >&2
  exit 1
fi

echo "==> starting the backend on :$PORT"
# `exec` so the subshell is REPLACED by python: otherwise $! is the subshell and
# the trap kills that, leaving the server running and the port held.
( cd "$REPO/backend" && exec env QUIZ_DB_PATH="$DB" BOT_TOKEN="$CAPTURE_BOT_TOKEN" \
    PUBLIC_URL="$CAPTURE_BASE_URL" \
    python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --log-level warning \
    > "$WORK/server.log" 2>&1 ) &
SERVER_PID=$!

for _ in $(seq 1 40); do
  if curl -fsS -o /dev/null "$CAPTURE_BASE_URL/api/quizzes" 2>/dev/null; then break; fi
  sleep 0.25
done
curl -fsS -o /dev/null "$CAPTURE_BASE_URL/api/quizzes" || { echo "backend did not start:"; cat "$WORK/server.log"; exit 1; }

echo "==> capturing"
if ! node "$REPO/scripts/capture/capture.mjs" "$@"; then
  echo "--- server log ---"; tail -40 "$WORK/server.log"; exit 1
fi
echo "==> done"
