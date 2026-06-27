import hashlib
import os
import re
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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
_asset_ver = None


def _compute_asset_version():
    """Short hash of the frontend bundle, used to cache-bust asset URLs.
    Changes automatically whenever app.js/styles.css change, so a deploy can
    never serve a stale Cloudflare-cached bundle."""
    h = hashlib.sha256()
    for fn in ("app.js", "ui.js", "styles.css"):
        p = os.path.join(_frontend_dir, fn)
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:8]


if os.path.isdir(_frontend_dir):
    # Serve index.html dynamically so its app.js/styles.css URLs always carry the
    # current bundle version. index.html is never edge-cached (Cloudflare DYNAMIC),
    # so the freshly-stamped version reaches the client every load.
    @app.get("/app", include_in_schema=False)
    @app.get("/app/", include_in_schema=False)
    def _serve_index():
        global _asset_ver
        if _asset_ver is None:
            _asset_ver = _compute_asset_version()
        with open(os.path.join(_frontend_dir, "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        html = re.sub(
            r"(app\.js|ui\.js|styles\.css)\?v=[A-Za-z0-9_]+",
            lambda m: f"{m.group(1)}?v={_asset_ver}",
            html,
        )
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})

    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="app")

_content_dir = os.path.join(os.path.dirname(__file__), "..", "..", "content")
if os.path.isdir(_content_dir):
    app.mount("/content", StaticFiles(directory=_content_dir), name="content")
