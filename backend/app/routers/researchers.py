import uuid
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Cadence, Researcher, Topic
from app.schemas import (
    AuthorSearchResult,
    FollowResearcherRequest,
    FollowResearcherResponse,
    ResearcherOut,
    TopicOut,
)
from app.services import researcher_enrichment
from app.services.aggregator import ingest_researcher_works
from app.services.scheduler import schedule_topic, unschedule_topic
from app.services.sources import openalex

router = APIRouter(prefix="/api/researchers", tags=["researchers"])


def _start_following(db: Session, researcher: Researcher, cadence: Cadence) -> FollowResearcherResponse:
    """Shared by /follow (openalex_id known upfront) and /{id}/track (an
    author from a paper we already have locally, openalex_id maybe not)."""
    existing_topic = db.query(Topic).filter(Topic.researcher_id == researcher.id).first()
    if existing_topic:
        raise HTTPException(400, "Already following this person")

    topic = Topic(raw_query=f"Works by {researcher.name}", researcher_id=researcher.id, cadence=cadence)
    db.add(topic)
    db.commit()
    db.refresh(researcher)
    db.refresh(topic)

    papers = ingest_researcher_works(db, researcher, topic.id)
    schedule_topic(topic)

    return FollowResearcherResponse(researcher=researcher, topic=topic, papers_found=len(papers))


@router.get("/search", response_model=list[AuthorSearchResult])
def search_researchers(q: str, limit: int = 10):
    """Look up a person by name — results aren't persisted until followed."""
    if not q.strip():
        return []
    return openalex.search_authors(q, limit=limit)


@router.get("/followed", response_model=list[dict])
def list_followed(db: Session = Depends(get_db)):
    """People whose work is being auto-ingested, for the People page."""
    topics = db.query(Topic).filter(Topic.researcher_id.isnot(None)).order_by(Topic.created_at.desc()).all()
    out = []
    for topic in topics:
        researcher = db.get(Researcher, topic.researcher_id)
        if not researcher:
            continue
        out.append(
            {
                "topic": TopicOut.model_validate(topic).model_dump(mode="json"),
                "researcher": ResearcherOut.model_validate(researcher).model_dump(mode="json"),
            }
        )
    return out


@router.post("/follow", response_model=FollowResearcherResponse)
def follow_researcher(payload: FollowResearcherRequest, db: Session = Depends(get_db)):
    """Follows a person: creates their profile if we don't have it, ingests
    everything they've written so far, and schedules ongoing refresh — the
    same "keeps showing up in Feed automatically" behavior as a topic."""
    researcher = db.query(Researcher).filter(Researcher.openalex_id == payload.openalex_id).first()
    if not researcher:
        author = openalex.get_author(payload.openalex_id)
        if not author:
            raise HTTPException(404, "Could not find that person on OpenAlex")
        institutions = author.get("last_known_institutions") or []
        researcher = Researcher(
            name=author.get("display_name") or "Unknown",
            orcid=(author.get("orcid") or "").replace("https://orcid.org/", "") or None,
            openalex_id=author.get("id"),
            affiliation=institutions[0].get("display_name") if institutions else None,
            merged_openalex_ids=payload.merged_ids or None,
        )
        db.add(researcher)
        db.flush()
    elif payload.merged_ids:
        # Already followed via a different search hit for the same person —
        # fold in any newly-seen duplicate OpenAlex ids so scheduled refresh
        # (services/scheduler.py) keeps covering all of them too.
        existing_merged = set(researcher.merged_openalex_ids or [])
        researcher.merged_openalex_ids = sorted(existing_merged | set(payload.merged_ids))

    return _start_following(db, researcher, payload.cadence)


@router.post("/{researcher_id}/track", response_model=FollowResearcherResponse)
def track_existing_researcher(researcher_id: uuid.UUID, cadence: Cadence = Cadence.daily, db: Session = Depends(get_db)):
    """"Add to People" from a paper's author list — same as /follow, but
    starting from a Researcher we already have locally (they're an author on
    some paper) instead of an OpenAlex id picked from search results. If we
    don't have their OpenAlex id yet (common for PubMed-sourced or manually
    uploaded papers), resolve it by name so their profile still gets a real
    publication history rather than staying empty."""
    researcher = db.get(Researcher, researcher_id)
    if not researcher:
        raise HTTPException(404, "Researcher not found")

    if not researcher.openalex_id:
        candidates = openalex.search_authors(researcher.name, limit=5)
        best = max(
            candidates,
            key=lambda c: SequenceMatcher(None, researcher.name.lower(), (c["name"] or "").lower()).ratio(),
            default=None,
        )
        if best and SequenceMatcher(None, researcher.name.lower(), (best["name"] or "").lower()).ratio() >= 0.8:
            researcher.openalex_id = best["openalex_id"]
            researcher.affiliation = researcher.affiliation or best.get("affiliation")
            db.commit()
            db.refresh(researcher)

    return _start_following(db, researcher, cadence)


@router.delete("/follow/{topic_id}", status_code=204)
def unfollow_researcher(topic_id: uuid.UUID, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic or not topic.researcher_id:
        raise HTTPException(404, "Follow not found")
    unschedule_topic(topic_id)
    db.delete(topic)
    db.commit()


@router.get("/{researcher_id}", response_model=ResearcherOut)
def get_researcher(researcher_id: uuid.UUID, enrich: bool = False, db: Session = Depends(get_db)):
    researcher = db.get(Researcher, researcher_id)
    if not researcher:
        raise HTTPException(404, "Researcher not found")

    if enrich and researcher.orcid and not researcher.degree:
        info = researcher_enrichment.enrich_from_orcid(researcher.orcid)
        researcher.degree = researcher.degree or info["degree"]
        researcher.affiliation = researcher.affiliation or info["affiliation"]
        db.commit()
        db.refresh(researcher)

    if enrich and researcher.faculty_page_url and not researcher.photo_url:
        scraped = researcher_enrichment.scrape_faculty_bio(researcher.faculty_page_url)
        researcher.photo_url = researcher.photo_url or scraped["photo_url"]
        researcher.degree = researcher.degree or scraped["degree"]
        db.commit()
        db.refresh(researcher)

    return researcher


@router.get("/{researcher_id}/publications")
def get_researcher_publications(researcher_id: uuid.UUID, db: Session = Depends(get_db)):
    researcher = db.get(Researcher, researcher_id)
    if not researcher:
        raise HTTPException(404, "Researcher not found")
    if not researcher.openalex_id:
        return []
    return openalex.get_author_works(researcher.openalex_id)
