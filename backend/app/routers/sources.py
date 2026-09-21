import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Source
from app.schemas import SourceIn, SourceOut

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), track: str | None = None):
    query = db.query(Source)
    if track:
        query = query.filter(Source.track == track)
    return query.order_by(Source.priority, Source.name).all()


@router.post("", response_model=SourceOut)
def create_source(payload: SourceIn, db: Session = Depends(get_db)):
    source = Source(**payload.model_dump(), is_user_added=True)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: uuid.UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    if not source.is_user_added:
        raise HTTPException(400, "Cannot delete a built-in curated source")
    db.delete(source)
    db.commit()
