from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AppSettings
from app.schemas import AppSettingsIn, AppSettingsOut
from app.services import settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])

_SECRET_FIELDS = ["anthropic_api_key", "ncbi_api_key", "semantic_scholar_api_key", "core_api_key"]
_PLAIN_FIELDS = ["unpaywall_email", "openalex_mailto"]


def _get_or_create_row(db: Session) -> AppSettings:
    row = db.query(AppSettings).first()
    if not row:
        row = AppSettings()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=AppSettingsOut)
def get_app_settings(db: Session = Depends(get_db)):
    row = db.query(AppSettings).first()
    env = get_settings()

    out: dict = {}
    for field in _SECRET_FIELDS:
        db_value = getattr(row, field, None) if row else None
        env_value = getattr(env, field, None)
        out[f"{field}_set"] = bool(db_value or env_value)
        out[f"{field}_source"] = "settings" if db_value else ("env" if env_value else "unset")
    for field in _PLAIN_FIELDS:
        db_value = getattr(row, field, None) if row else None
        env_value = getattr(env, field, None)
        out[field] = db_value or env_value
        out[f"{field}_source"] = "settings" if db_value else ("env" if env_value else "unset")
    return AppSettingsOut(**out)


@router.patch("", response_model=AppSettingsOut)
def update_app_settings(payload: AppSettingsIn, db: Session = Depends(get_db)):
    """A field left out of the body is untouched; an empty string clears the
    override back to whatever .env provides (see AppSettingsIn)."""
    row = _get_or_create_row(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value or None)
    db.commit()
    settings_store.invalidate_cache()
    return get_app_settings(db)
