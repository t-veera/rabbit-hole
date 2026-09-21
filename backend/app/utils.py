"""Small cross-router helpers."""

import uuid

from sqlalchemy.orm import Session

from app.models import ItemType, ReadingStatus


def attach_reading_status(db: Session, item_type: ItemType, items: list) -> None:
    """Sets a transient `.reading_status` attribute on each ORM item (not persisted),
    so PaperOut/ArticleOut can serialize it without a real FK relationship
    (item_id is a generic UUID that can point at either papers or articles).
    """
    if not items:
        return
    ids = [item.id for item in items]
    rows = (
        db.query(ReadingStatus)
        .filter(ReadingStatus.item_type == item_type, ReadingStatus.item_id.in_(ids))
        .all()
    )
    by_id = {row.item_id: row for row in rows}
    for item in items:
        item.reading_status = by_id.get(item.id)


def get_or_create_reading_status(db: Session, item_type: ItemType, item_id: uuid.UUID) -> ReadingStatus:
    row = (
        db.query(ReadingStatus)
        .filter(ReadingStatus.item_type == item_type, ReadingStatus.item_id == item_id)
        .first()
    )
    if row:
        return row
    row = ReadingStatus(item_type=item_type, item_id=item_id)
    db.add(row)
    db.flush()
    return row
