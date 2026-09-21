"""In-process APScheduler background jobs — one recurring job per topic.

Cadence setting per topic controls refresh frequency (spec: real-time vs
daily vs weekly). True push-based "real-time" isn't available from any of
these upstream APIs, so "real-time" here means a short poll interval.
"""

from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db import SessionLocal
from app.models import Cadence, Researcher, Topic
from app.services.aggregator import ingest_researcher_works, run_search

_CADENCE_SECONDS = {
    Cadence.realtime: 15 * 60,
    Cadence.daily: 24 * 60 * 60,
    Cadence.weekly: 7 * 24 * 60 * 60,
}

scheduler = BackgroundScheduler()


def _job_id(topic_id) -> str:
    return f"topic-refresh-{topic_id}"


def _run_topic_refresh(topic_id) -> None:
    db = SessionLocal()
    try:
        topic = db.get(Topic, topic_id)
        if not topic:
            return
        if topic.researcher_id:
            researcher = db.get(Researcher, topic.researcher_id)
            if researcher:
                ingest_researcher_works(db, researcher, topic.id)
        elif topic.translated_query:
            run_search(db, topic.translated_query, topic.field, topic_id=topic.id)
        else:
            return
        topic.last_run_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def schedule_topic(topic: Topic) -> None:
    seconds = _CADENCE_SECONDS.get(topic.cadence, _CADENCE_SECONDS[Cadence.daily])
    scheduler.add_job(
        _run_topic_refresh,
        trigger=IntervalTrigger(seconds=seconds),
        args=[topic.id],
        id=_job_id(topic.id),
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def unschedule_topic(topic_id) -> None:
    job_id = _job_id(topic_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def start() -> None:
    if not scheduler.running:
        scheduler.start()


def load_existing_topics() -> None:
    """Called once at app startup to re-register jobs for topics saved from a prior run."""
    db = SessionLocal()
    try:
        for topic in db.query(Topic).all():
            schedule_topic(topic)
    finally:
        db.close()
