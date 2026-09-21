import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Book, ItemType
from app.schemas import BookOut
from app.utils import attach_reading_status

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: uuid.UUID, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    attach_reading_status(db, ItemType.book, [book])
    return book
