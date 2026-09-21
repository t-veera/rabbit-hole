from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Topic
from app.schemas import SearchRunRequest, SearchRunResponse, TranslateRequest, TranslateResponse
from app.services.aggregator import run_search
from app.services.llm import translate_query
from app.services.scheduler import schedule_topic

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest):
    translated, field = translate_query(payload.raw_query)
    return TranslateResponse(raw_query=payload.raw_query, translated_query=translated, inferred_field=field)


@router.post("/run", response_model=SearchRunResponse)
def run(payload: SearchRunRequest, db: Session = Depends(get_db)):
    translated, inferred_field = translate_query(payload.raw_query)
    field = payload.field or inferred_field

    topic_id = None
    if payload.save_as_topic:
        topic = Topic(
            raw_query=payload.raw_query,
            translated_query=translated,
            field=field,
            cadence=payload.cadence,
        )
        db.add(topic)
        db.commit()
        db.refresh(topic)
        schedule_topic(topic)
        topic_id = topic.id

    result = run_search(db, translated, field, topic_id=topic_id, raw_query=payload.raw_query)
    return SearchRunResponse(
        translated_query=translated,
        inferred_field=field,
        papers=result["papers"],
        articles=result["articles"],
        books=result["books"],
        topic_id=topic_id,
    )
