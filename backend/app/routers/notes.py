import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Article, ItemType, ListItem, Note, Paper
from app.schemas import NoteIn, NoteOut, NotePatch
from app.services.export import notes_to_markdown, notes_to_plain_text

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=list[NoteOut])
def list_notes(
    db: Session = Depends(get_db),
    topic_tag: str | None = None,
    item_type: ItemType | None = None,
    item_id: uuid.UUID | None = None,
    freeform: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    query = db.query(Note)
    if topic_tag:
        query = query.filter(Note.topic_tag == topic_tag)
    if item_type:
        query = query.filter(Note.item_type == item_type)
    if item_id:
        query = query.filter(Note.item_id == item_id)
    if freeform is True:
        query = query.filter(Note.item_id.is_(None))
    elif freeform is False:
        query = query.filter(Note.item_id.isnot(None))
    if date_from:
        query = query.filter(Note.created_at >= date_from)
    if date_to:
        query = query.filter(Note.created_at <= date_to)
    return query.order_by(Note.created_at.desc()).all()


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    return note


@router.post("", response_model=NoteOut)
def create_note(payload: NoteIn, db: Session = Depends(get_db)):
    note = Note(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.patch("/{note_id}", response_model=NoteOut)
def patch_note(note_id: uuid.UUID, payload: NotePatch, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    # item_id isn't a real FK (it's polymorphic across papers/articles/books/
    # notes — see models.ListItem), so nothing cascades this automatically:
    # without it, a note that's been added to a list would leave that list's
    # detail page permanently broken (dangling reference -> 404 -> unhandled
    # rejection -> stuck "Loading...").
    db.query(ListItem).filter(ListItem.item_type == ItemType.note, ListItem.item_id == note_id).delete()
    db.delete(note)
    db.commit()


@router.get("/export/run")
def export_notes(
    db: Session = Depends(get_db),
    format: str = Query("markdown", pattern="^(markdown|text)$"),
    topic_tag: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    query = db.query(Note)
    if topic_tag:
        query = query.filter(Note.topic_tag == topic_tag)
    if date_from:
        query = query.filter(Note.created_at >= date_from)
    if date_to:
        query = query.filter(Note.created_at <= date_to)
    notes = query.order_by(Note.created_at).all()

    paper_ids = [n.item_id for n in notes if n.item_type == ItemType.paper]
    article_ids = [n.item_id for n in notes if n.item_type == ItemType.article]
    titles = {(ItemType.paper, p.id): p.title for p in db.query(Paper).filter(Paper.id.in_(paper_ids)).all()}
    titles.update(
        {(ItemType.article, a.id): a.title for a in db.query(Article).filter(Article.id.in_(article_ids)).all()}
    )

    if format == "markdown":
        content = notes_to_markdown(notes, titles)
        media_type = "text/markdown"
    else:
        content = notes_to_plain_text(notes, titles)
        media_type = "text/plain"
    return PlainTextResponse(content, media_type=media_type)
