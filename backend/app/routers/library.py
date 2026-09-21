from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Article, Book, ItemType, Note, Paper
from app.schemas import ArticleOut, BookOut, NoteOut, PaperOut
from app.utils import attach_reading_status

router = APIRouter(prefix="/api/library", tags=["library"])


class LibrarySearchOut(BaseModel):
    papers: list[PaperOut]
    articles: list[ArticleOut]
    books: list[BookOut]
    notes: list[NoteOut]


@router.get("/search", response_model=LibrarySearchOut)
def search_library(q: str, db: Session = Depends(get_db), limit: int = 25):
    pattern = f"%{q}%"

    papers = (
        db.query(Paper)
        .filter(or_(Paper.title.ilike(pattern), Paper.abstract.ilike(pattern), Paper.full_text.ilike(pattern)))
        .limit(limit)
        .all()
    )
    articles = (
        db.query(Article)
        .filter(or_(Article.title.ilike(pattern), Article.summary.ilike(pattern)))
        .limit(limit)
        .all()
    )
    books = (
        db.query(Book)
        .filter(or_(Book.title.ilike(pattern), Book.description.ilike(pattern)))
        .limit(limit)
        .all()
    )
    notes = db.query(Note).filter(Note.note_text.ilike(pattern)).limit(limit).all()

    attach_reading_status(db, ItemType.paper, papers)
    attach_reading_status(db, ItemType.article, articles)
    attach_reading_status(db, ItemType.book, books)

    return LibrarySearchOut(papers=papers, articles=articles, books=books, notes=notes)
