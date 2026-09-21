import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import SessionLocal
from app.models import Source, SourceKind, SourceTrack
from app.routers import (
    books,
    feed,
    graph,
    items,
    journalism,
    library,
    lists,
    notes,
    papers,
    researchers,
    search,
    settings as settings_router,
    sources,
    topics,
)
from app.services import scheduler

_CURATED_JOURNALISM_SOURCES = [
    ("Aeon", "https://aeon.co/feed.rss"),
    ("Quanta Magazine", "https://www.quantamagazine.org/feed/"),
    ("Nature News", "https://www.nature.com/nature.rss"),
    ("Science News", "https://www.sciencenews.org/feed"),
]


def _seed_curated_sources() -> None:
    db = SessionLocal()
    try:
        for name, url in _CURATED_JOURNALISM_SOURCES:
            exists = db.query(Source).filter(Source.url == url).first()
            if exists:
                continue
            db.add(
                Source(
                    name=name,
                    url=url,
                    kind=SourceKind.rss,
                    track=SourceTrack.journalism,
                    is_user_added=False,
                    priority=100,
                )
            )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_curated_sources()
    scheduler.start()
    scheduler.load_existing_topics()
    yield
    scheduler.scheduler.shutdown(wait=False)


app = FastAPI(title="Rabbit Hole", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(topics.router)
app.include_router(feed.router)
app.include_router(journalism.router)
app.include_router(papers.router)
app.include_router(books.router)
app.include_router(items.router)
app.include_router(researchers.router)
app.include_router(sources.router)
app.include_router(lists.router)
app.include_router(notes.router)
app.include_router(graph.router)
app.include_router(library.router)
app.include_router(settings_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Serve the built frontend, when present ---
#
# In normal local dev (README's two-terminal flow) `frontend/dist` doesn't
# exist and nothing below this line ever activates — Vite's own dev server
# serves the frontend instead. The packaged desktop app (see
# desktop/build_backend.py) runs `npm run build` first and points
# FRONTEND_DIST_DIR at the bundled build, so the backend becomes the only
# server the packaged app needs to run.
#
# This must stay registered after every app.include_router() call above:
# Starlette matches routes in registration order, and the catch-all path
# below would otherwise shadow real API routes instead of only catching
# what nothing else matched.
_default_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_frontend_dist = Path(os.environ.get("FRONTEND_DIST_DIR", _default_frontend_dist))

if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404)
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
