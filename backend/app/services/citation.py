"""Derives citation graph edges from OpenAlex cites/cited-by data.

Only creates edges between two papers that already exist in the local DB
(both sides must be saved/discovered items) — this is the "Auto/citation"
edge type in the graph view, kept visually distinct from user-drawn
"Manual" edges and toggleable as a layer.
"""

from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models import EdgeType, GraphEdge, ItemType, Paper
from app.services.sources import openalex

_TITLE_MATCH_THRESHOLD = 0.6


def refresh_citation_edges_for_paper(db: Session, paper: Paper) -> int:
    if not paper.openalex_id:
        return 0

    links = openalex.get_work_citations(paper.openalex_id)
    related_ids = set(links["cites"]) | set(links["cited_by"])
    if not related_ids:
        return 0

    local_matches = db.query(Paper).filter(Paper.openalex_id.in_(related_ids)).all()
    created = 0
    for other in local_matches:
        if other.id == paper.id:
            continue
        is_citing = other.openalex_id in links["cites"]
        source, target = (paper, other) if is_citing else (other, paper)

        exists = (
            db.query(GraphEdge)
            .filter(
                GraphEdge.source_type == ItemType.paper,
                GraphEdge.source_id == source.id,
                GraphEdge.target_type == ItemType.paper,
                GraphEdge.target_id == target.id,
                GraphEdge.edge_type == EdgeType.citation,
            )
            .first()
        )
        if exists:
            continue

        db.add(
            GraphEdge(
                source_type=ItemType.paper,
                source_id=source.id,
                target_type=ItemType.paper,
                target_id=target.id,
                edge_type=EdgeType.citation,
            )
        )
        created += 1

    db.commit()
    return created


def enrich_uploaded_paper(db: Session, paper: Paper) -> None:
    """Finds this uploaded paper's OpenAlex record — by DOI if we have one,
    otherwise by matching its title against OpenAlex search results — so it
    gets citation edges the same as anything auto-fetched. Best-effort: does
    nothing (silently) if no confident match exists, per spec — an upload
    with clean metadata should get enriched, not blocked on it."""
    if paper.openalex_id:
        return

    match: dict | None = None
    if paper.doi:
        work = openalex.get_work_by_doi(paper.doi)
        if work:
            match = work
    if not match and paper.title:
        candidates = openalex.search(paper.title, per_page=5)
        for candidate in candidates:
            similarity = SequenceMatcher(None, paper.title.lower(), candidate["title"].lower()).ratio()
            if similarity >= _TITLE_MATCH_THRESHOLD:
                match = candidate
                break

    if not match or not match.get("openalex_id"):
        return

    paper.openalex_id = match["openalex_id"]
    if not paper.abstract and match.get("abstract"):
        paper.abstract = match["abstract"]
    if not paper.oa_url and match.get("oa_url"):
        paper.oa_url = match["oa_url"]
        paper.oa_status = paper.oa_status or bool(match.get("oa_status"))
    db.commit()

    refresh_citation_edges_for_paper(db, paper)
