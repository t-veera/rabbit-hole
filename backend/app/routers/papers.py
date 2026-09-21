import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.db import SessionLocal, get_db
from app.models import EdgeType, GraphEdge, ItemType, Paper, PaperOrigin
from app.schemas import GraphEdgeOut, PaperOut, UploadConfirmRequest, UploadDraft
from app.services import fulltext, upload as upload_service
from app.services.aggregator import _upsert_paper
from app.services.citation import enrich_uploaded_paper, refresh_citation_edges_for_paper
from app.services.export import to_bibtex, to_ris
from app.utils import attach_reading_status

router = APIRouter(prefix="/api/papers", tags=["papers"])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@router.post("/upload", response_model=UploadDraft)
async def upload_pdf(file: UploadFile):
    """Step 1 of manual upload: extract text + best-effort metadata, no DB write
    yet. The frontend shows this as an editable draft before confirm persists it."""
    if file.content_type not in ("application/pdf", "application/octet-stream", None):
        raise HTTPException(415, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF is too large (50MB limit)")
    if pdf_bytes[:5] != b"%PDF-":
        raise HTTPException(415, "That doesn't look like a PDF")

    try:
        text = fulltext.extract_text_for_upload(pdf_bytes)
    except fulltext.OcrUnavailable:
        raise HTTPException(
            422,
            "This PDF has no real text layer (looks scanned) and needs OCR to read — "
            "but Tesseract isn't installed on this server yet. Ask whoever runs this "
            "instance to install it (`tesseract` + `tesseract-data-eng`), then try again.",
        )
    if not text:
        raise HTTPException(422, "Couldn't extract any readable text from this PDF.")

    draft = upload_service.extract_draft(pdf_bytes)

    return UploadDraft(
        suggested_title=draft["suggested_title"],
        suggested_authors=draft["suggested_authors"],
        suggested_doi=draft["suggested_doi"],
        full_text=text,
        page_count=draft["page_count"],
    )


def _enrich_uploaded_paper_task(paper_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        paper = db.get(Paper, paper_id)
        if paper:
            enrich_uploaded_paper(db, paper)
    finally:
        db.close()


@router.post("/upload/confirm", response_model=PaperOut)
def confirm_upload(payload: UploadConfirmRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Step 2: persists the (user-reviewed) draft as a real Paper — bookmarkable,
    listable, highlightable, graphable, searchable, same as any other paper —
    then kicks off citation-graph enrichment in the background (DOI if present,
    else a title match against OpenAlex; see services/citation.py)."""
    if payload.attach_to_paper_id:
        paper = db.get(Paper, payload.attach_to_paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        paper.full_text = payload.full_text
        paper.doi = paper.doi or payload.doi
        paper.venue = paper.venue or payload.venue
        db.commit()
        db.refresh(paper)
        attach_reading_status(db, ItemType.paper, [paper])
        return paper

    record = {
        "title": payload.title,
        "abstract": None,
        "doi": payload.doi,
        "external_id": None,
        "venue": payload.venue,
        "published_date": payload.published_date,
        "landing_url": None,
        "oa_url": None,
        "oa_status": False,
        "openalex_id": None,
        "authors": [{"name": name} for name in payload.authors],
        "raw_metadata": {"source": "upload"},
    }
    paper = _upsert_paper(db, record, topic_id=None, origin=PaperOrigin.uploaded, origin_source_id=None)
    paper.full_text = payload.full_text
    db.commit()
    db.refresh(paper)

    background_tasks.add_task(_enrich_uploaded_paper_task, paper.id)

    attach_reading_status(db, ItemType.paper, [paper])
    return paper


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: uuid.UUID, db: Session = Depends(get_db)):
    paper = (
        db.query(Paper)
        .options(joinedload(Paper.origin_source), joinedload(Paper.authors))
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(404, "Paper not found")
    attach_reading_status(db, ItemType.paper, [paper])
    return paper


@router.post("/{paper_id}/dismiss", response_model=PaperOut)
def dismiss_paper(paper_id: uuid.UUID, db: Session = Depends(get_db)):
    """Hides a paper from the feed without deleting it — lists, notes, and
    the citation graph can still reference it. See Topic's reset-dismissed
    (routers/topics.py) for bringing dismissed papers back."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")
    paper.dismissed = True
    db.commit()
    db.refresh(paper)
    attach_reading_status(db, ItemType.paper, [paper])
    return paper


@router.get("/{paper_id}/citations", response_model=list[GraphEdgeOut])
def get_paper_citations(paper_id: uuid.UUID, refresh: bool = False, db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")
    if refresh:
        refresh_citation_edges_for_paper(db, paper)

    edges = (
        db.query(GraphEdge)
        .filter(
            GraphEdge.edge_type == EdgeType.citation,
            ((GraphEdge.source_type == ItemType.paper) & (GraphEdge.source_id == paper_id))
            | ((GraphEdge.target_type == ItemType.paper) & (GraphEdge.target_id == paper_id)),
        )
        .all()
    )
    return edges


@router.get("/{paper_id}/fulltext-text")
def get_fulltext_text(paper_id: uuid.UUID, refresh: bool = False, db: Session = Depends(get_db)):
    """Fetches this paper's full text — see services/fulltext.py:resolve_fulltext
    for the resolution chain (Europe PMC -> Unpaywall OA copies -> CORE.ac.uk)."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")
    return fulltext.resolve_fulltext(db, paper, refresh=refresh)


@router.get("/{paper_id}/export")
def export_paper(paper_id: uuid.UUID, format: str = Query("bibtex", pattern="^(bibtex|ris)$"), db: Session = Depends(get_db)):
    paper = (
        db.query(Paper).options(joinedload(Paper.authors)).filter(Paper.id == paper_id).first()
    )
    if not paper:
        raise HTTPException(404, "Paper not found")
    content = to_bibtex(paper) if format == "bibtex" else to_ris(paper)
    media_type = "application/x-bibtex" if format == "bibtex" else "application/x-research-info-systems"
    return PlainTextResponse(content, media_type=media_type)
