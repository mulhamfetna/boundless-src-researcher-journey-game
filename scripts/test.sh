#!/usr/bin/env bash
# Run the full test suite: backend (pytest) + frontend (Vitest).
# Usage: ./scripts/test.sh   (from the repo root)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== backend (pytest) =="
( cd "$ROOT/backend" && python3 -m pytest -q )

echo
echo "== frontend (Vitest + jsdom) =="
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "frontend deps missing — installing (npm install)…"
  ( cd "$ROOT/frontend" && npm install )
fi
( cd "$ROOT/frontend" && npm test )

echo
echo "== frontend drag e2e (real browser; skips if no Chrome) =="
( cd "$ROOT/frontend" && node tests/drag.e2e.mjs )

echo "== frontend phone play-area e2e (360x640; skips if no Chrome) =="
( cd "$ROOT/frontend" && node tests/phone.e2e.mjs )

echo
echo "All suites passed."
