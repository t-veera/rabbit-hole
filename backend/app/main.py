from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
