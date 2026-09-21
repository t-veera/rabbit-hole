"""Resolves API keys/config that a user can set from the Settings page,
layering a small DB-backed override on top of the .env-derived defaults in
app/config.py — so saving a key in the UI takes effect immediately, with no
process restart, for every source module that already reads get_settings().

Cached in-process (invalidated on save) rather than hitting Postgres on every
call, since these values are read once per search/refresh but read from
inside a concurrent fan-out (see services/aggregator.py's per-DOI Unpaywall
lookups) where N simultaneous DB round-trips would be wasteful.
"""

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.models import AppSettings

_OVERRIDABLE_FIELDS = [
    "anthropic_api_key",
    "unpaywall_email",
    "openalex_mailto",
    "ncbi_api_key",
    "semantic_scholar_api_key",
    "core_api_key",
]

_cache: dict[str, str] | None = None


def _load_from_db() -> dict[str, str]:
    db = SessionLocal()
    try:
        row = db.query(AppSettings).first()
    finally:
        db.close()
    if not row:
        return {}
    return {field: value for field in _OVERRIDABLE_FIELDS if (value := getattr(row, field))}


def effective_settings() -> Settings:
    global _cache
    if _cache is None:
        _cache = _load_from_db()
    base = get_settings()
    if not _cache:
        return base
    return base.model_copy(update=_cache)


def invalidate_cache() -> None:
    global _cache
    _cache = None
