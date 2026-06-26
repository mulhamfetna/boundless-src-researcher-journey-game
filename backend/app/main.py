import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_schema

# Shared connection, set during the lifespan startup (or overridden in tests).
_conn = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _conn
    if _conn is None:
        conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        init_schema(conn)
        _conn = conn
    app.state.conn = _conn
    yield


app = FastAPI(title="Gamified Quiz", lifespan=lifespan)


@app.middleware("http")
async def _no_cache_mini_app(request, call_next):
    # The Mini App static assets (/app/*) must never be edge/browser cached
    # stale: Cloudflare otherwise caches app.js/styles.css for hours, serving an
    # old bundle against fresh index.html. no-cache forces revalidation via etag.
    response = await call_next(request)
    if request.url.path.startswith("/app"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


from app.api import router as api_router  # noqa: E402
app.include_router(api_router)

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="app")

_content_dir = os.path.join(os.path.dirname(__file__), "..", "..", "content")
if os.path.isdir(_content_dir):
    app.mount("/content", StaticFiles(directory=_content_dir), name="content")
