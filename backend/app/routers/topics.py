import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Topic
from app.schemas import NotificationOut, TopicIn, TopicOut, TopicPatch
from app.services.aggregator import run_search
from app.services.llm import translate_query
from app.services.scheduler import schedule_topic, unschedule_topic

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    return db.query(Topic).order_by(Topic.created_at.desc()).all()


@router.post("", response_model=TopicOut)
def create_topic(payload: TopicIn, db: Session = Depends(get_db)):
    translated, inferred_field = translate_query(payload.raw_query)
    field = payload.field or inferred_field

    topic = Topic(raw_query=payload.raw_query, translated_query=translated, field=field, cadence=payload.cadence)
    db.add(topic)
    db.commit()
    db.refresh(topic)

    run_search(db, translated, field, topic_id=topic.id)
    schedule_topic(topic)
    return topic


@router.patch("/{topic_id}", response_model=TopicOut)
def patch_topic(topic_id: uuid.UUID, payload: TopicPatch, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    if payload.cadence is not None:
        topic.cadence = payload.cadence
    if payload.field is not None:
        topic.field = payload.field
    db.commit()
    db.refresh(topic)
    schedule_topic(topic)  # reschedule with new cadence if it changed
    return topic


@router.delete("/{topic_id}", status_code=204)
def delete_topic(topic_id: uuid.UUID, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    unschedule_topic(topic_id)
    db.delete(topic)
    db.commit()


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db)):
    """New-items-since-last-visit indicator, per active topic."""
    from app.models import Article, Paper, SeenLog

    out = []
    for topic in db.query(Topic).all():
        seen = db.query(SeenLog).filter(SeenLog.topic_id == topic.id).first()
        since = seen.last_seen_at if seen else topic.created_at
        paper_count = db.query(Paper).filter(Paper.topic_id == topic.id, Paper.created_at > since).count()
        article_count = db.query(Article).filter(Article.topic_id == topic.id, Article.created_at > since).count()
        new_count = paper_count + article_count
        if new_count:
            out.append(NotificationOut(topic_id=topic.id, topic_query=topic.raw_query, new_count=new_count))
    return out


@router.post("/{topic_id}/reset-dismissed", status_code=204)
def reset_dismissed(topic_id: uuid.UUID, db: Session = Depends(get_db)):
    """Un-hides every paper dismissed from this topic's feed — see
    routers/papers.py:dismiss_paper. Only clears the flag, never deletes."""
    from app.models import Paper

    if not db.get(Topic, topic_id):
        raise HTTPException(404, "Topic not found")
    db.query(Paper).filter(Paper.topic_id == topic_id, Paper.dismissed.is_(True)).update({"dismissed": False})
    db.commit()


@router.post("/{topic_id}/mark-seen", status_code=204)
def mark_seen(topic_id: uuid.UUID, db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    from app.models import SeenLog

    seen = db.query(SeenLog).filter(SeenLog.topic_id == topic_id).first()
    if seen:
        seen.last_seen_at = datetime.now(timezone.utc)
    else:
        db.add(SeenLog(topic_id=topic_id))
    db.commit()
