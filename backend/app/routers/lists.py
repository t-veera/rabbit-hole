import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import ItemType, List, ListItem, Paper
from app.schemas import ListIn, ListItemIn, ListItemOut, ListOut
from app.services.export import to_bibtex, to_ris

router = APIRouter(prefix="/api/lists", tags=["lists"])


@router.get("", response_model=list[ListOut])
def list_lists(db: Session = Depends(get_db)):
    return db.query(List).order_by(List.created_at).all()


@router.post("", response_model=ListOut)
def create_list(payload: ListIn, db: Session = Depends(get_db)):
    lst = List(name=payload.name)
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return lst


@router.delete("/{list_id}", status_code=204)
def delete_list(list_id: uuid.UUID, db: Session = Depends(get_db)):
    lst = db.get(List, list_id)
    if not lst:
        raise HTTPException(404, "List not found")
    db.delete(lst)
    db.commit()


@router.get("/{list_id}/items", response_model=list[ListItemOut])
def get_list_items(list_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(ListItem).filter(ListItem.list_id == list_id).all()


@router.post("/{list_id}/items", response_model=ListItemOut)
def add_list_item(list_id: uuid.UUID, payload: ListItemIn, db: Session = Depends(get_db)):
    if not db.get(List, list_id):
        raise HTTPException(404, "List not found")
    existing = (
        db.query(ListItem)
        .filter(
            ListItem.list_id == list_id,
            ListItem.item_type == payload.item_type,
            ListItem.item_id == payload.item_id,
        )
        .first()
    )
    if existing:
        return existing
    item = ListItem(list_id=list_id, item_type=payload.item_type, item_id=payload.item_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{list_id}/items/{item_id}", status_code=204)
def remove_list_item(list_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)):
    item = (
        db.query(ListItem).filter(ListItem.list_id == list_id, ListItem.id == item_id).first()
    )
    if not item:
        raise HTTPException(404, "List item not found")
    db.delete(item)
    db.commit()


@router.get("/{list_id}/export")
def export_list(list_id: uuid.UUID, format: str = Query("bibtex", pattern="^(bibtex|ris)$"), db: Session = Depends(get_db)):
    items = db.query(ListItem).filter(ListItem.list_id == list_id, ListItem.item_type == ItemType.paper).all()
    paper_ids = [i.item_id for i in items]
    papers = db.query(Paper).options(joinedload(Paper.authors)).filter(Paper.id.in_(paper_ids)).all()
    entries = [to_bibtex(p) if format == "bibtex" else to_ris(p) for p in papers]
    separator = "\n\n" if format == "bibtex" else "\n"
    media_type = "application/x-bibtex" if format == "bibtex" else "application/x-research-info-systems"
    return PlainTextResponse(separator.join(entries), media_type=media_type)
