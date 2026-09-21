"""Reading status + queue/reference state — shared across papers and articles
since item_id is a generic UUID that can point at either table.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ItemType
from app.schemas import ReadingStatusOut, ReadingStatusPatch
from app.utils import get_or_create_reading_status

router = APIRouter(prefix="/api/items", tags=["items"])


@router.patch("/{item_type}/{item_id}/status", response_model=ReadingStatusOut)
def patch_status(item_type: ItemType, item_id: uuid.UUID, payload: ReadingStatusPatch, db: Session = Depends(get_db)):
    status_row = get_or_create_reading_status(db, item_type, item_id)
    if payload.status is not None:
        status_row.status = payload.status
    if payload.in_queue is not None:
        status_row.in_queue = payload.in_queue
    if payload.in_reference is not None:
        status_row.in_reference = payload.in_reference
    db.commit()
    db.refresh(status_row)
    return status_row
