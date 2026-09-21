import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Article, ItemType, ReadingState, ReadingStatus
from app.schemas import ArticleOut
from app.services.article_fulltext import fetch_article_fulltext
from app.utils import attach_reading_status

router = APIRouter(prefix="/api/journalism", tags=["journalism"])


@router.get("", response_model=list[ArticleOut])
def get_journalism_feed(
    db: Session = Depends(get_db),
    topic_id: uuid.UUID | None = None,
    status: ReadingState | None = None,
    in_queue: bool | None = None,
    in_reference: bool | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = db.query(Article).options(joinedload(Article.origin_source))
    if topic_id:
        query = query.filter(Article.topic_id == topic_id)
    if status is not None or in_queue is not None or in_reference is not None:
        query = query.join(
            ReadingStatus,
            (ReadingStatus.item_type == ItemType.article) & (ReadingStatus.item_id == Article.id),
        )
        if status is not None:
            query = query.filter(ReadingStatus.status == status)
        if in_queue is not None:
            query = query.filter(ReadingStatus.in_queue.is_(in_queue))
        if in_reference is not None:
            query = query.filter(ReadingStatus.in_reference.is_(in_reference))

    articles = query.order_by(Article.published_date.desc().nulls_last()).offset(offset).limit(limit).all()
    attach_reading_status(db, ItemType.article, articles)
    return articles


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: uuid.UUID, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    attach_reading_status(db, ItemType.article, [article])
    return article


@router.get("/{article_id}/fulltext-text")
def get_article_fulltext(article_id: uuid.UUID, refresh: bool = False, db: Session = Depends(get_db)):
    """Same idea as papers' fulltext-text (routers/papers.py) — cached after
    the first successful fetch — but for articles there's no OA-copy chain
    to walk, just the article's own URL (services/article_fulltext.py)."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    if article.full_text and not refresh:
        return {"text": article.full_text, "source": "cache"}

    text = fetch_article_fulltext(article.url)
    if text:
        article.full_text = text
        db.commit()
        return {"text": text, "source": "source site"}

    return {"text": None, "source": None}
