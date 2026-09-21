import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import ItemType, Paper, PaperOrigin, ReadingState, ReadingStatus
from app.schemas import PaperOut
from app.utils import attach_reading_status

router = APIRouter(prefix="/api/feed", tags=["feed"])


_SORTS = {
    "published_desc": Paper.published_date.desc().nulls_last(),
    "published_asc": Paper.published_date.asc().nulls_last(),
    "added_desc": Paper.created_at.desc(),
    "added_asc": Paper.created_at.asc(),
    "title_asc": Paper.title.asc(),
}


@router.get("", response_model=list[PaperOut])
def get_feed(
    db: Session = Depends(get_db),
    field: str | None = None,
    topic_id: uuid.UUID | None = None,
    origin: PaperOrigin | None = None,
    status: ReadingState | None = None,
    exclude_status: ReadingState | None = None,
    in_queue: bool | None = None,
    in_reference: bool | None = None,
    sort: str = "published_desc",
    include_dismissed: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    query = db.query(Paper).options(
        joinedload(Paper.origin_source), joinedload(Paper.authors)
    )
    if not include_dismissed:
        query = query.filter(Paper.dismissed.is_(False))
    if field:
        query = query.filter(Paper.field == field)
    if topic_id:
        query = query.filter(Paper.topic_id == topic_id)
    if origin is not None:
        query = query.filter(Paper.origin == origin)

    if exclude_status is not None:
        # A NOT IN subquery, not an inner join + negated match — most papers
        # have no ReadingStatus row at all until first touched (see
        # utils.get_or_create_reading_status), and those must still pass an
        # "exclude read" filter rather than being dropped by it.
        excluded_ids = db.query(ReadingStatus.item_id).filter(
            ReadingStatus.item_type == ItemType.paper,
            ReadingStatus.status == exclude_status,
        )
        query = query.filter(Paper.id.notin_(excluded_ids))

    if status is not None or in_queue is not None or in_reference is not None:
        query = query.join(
            ReadingStatus,
            (ReadingStatus.item_type == ItemType.paper) & (ReadingStatus.item_id == Paper.id),
        )
        if status is not None:
            query = query.filter(ReadingStatus.status == status)
        if in_queue is not None:
            query = query.filter(ReadingStatus.in_queue.is_(in_queue))
        if in_reference is not None:
            query = query.filter(ReadingStatus.in_reference.is_(in_reference))

    order_by = _SORTS.get(sort, _SORTS["published_desc"])
    papers = query.order_by(order_by).offset(offset).limit(limit).all()
    attach_reading_status(db, ItemType.paper, papers)
    return papers
