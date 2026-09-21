import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Article, EdgeType, GraphEdge, ItemType, ListItem, Paper
from app.schemas import GraphEdgeIn, GraphEdgeOut, GraphNode, GraphOut

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _node_id(item_type: ItemType, item_id: uuid.UUID) -> str:
    return f"{item_type.value}:{item_id}"


@router.get("", response_model=GraphOut)
def get_graph(db: Session = Depends(get_db), include_citations: bool = True):
    edge_query = db.query(GraphEdge)
    if not include_citations:
        edge_query = edge_query.filter(GraphEdge.edge_type == EdgeType.manual)
    edges = edge_query.all()

    saved_paper_ids = {row.item_id for row in db.query(ListItem).filter(ListItem.item_type == ItemType.paper)}
    saved_article_ids = {row.item_id for row in db.query(ListItem).filter(ListItem.item_type == ItemType.article)}

    linked_keys: set[tuple[ItemType, uuid.UUID]] = set()
    for edge in edges:
        linked_keys.add((edge.source_type, edge.source_id))
        linked_keys.add((edge.target_type, edge.target_id))

    needed_paper_ids = saved_paper_ids | {i for (t, i) in linked_keys if t == ItemType.paper}
    needed_article_ids = saved_article_ids | {i for (t, i) in linked_keys if t == ItemType.article}

    papers = db.query(Paper).filter(Paper.id.in_(needed_paper_ids)).all() if needed_paper_ids else []
    articles = db.query(Article).filter(Article.id.in_(needed_article_ids)).all() if needed_article_ids else []

    nodes = [
        GraphNode(
            id=_node_id(ItemType.paper, p.id),
            item_type=ItemType.paper,
            item_id=p.id,
            title=p.title,
            is_saved=p.id in saved_paper_ids,
            is_linked=(ItemType.paper, p.id) in linked_keys,
        )
        for p in papers
    ] + [
        GraphNode(
            id=_node_id(ItemType.article, a.id),
            item_type=ItemType.article,
            item_id=a.id,
            title=a.title,
            is_saved=a.id in saved_article_ids,
            is_linked=(ItemType.article, a.id) in linked_keys,
        )
        for a in articles
    ]

    return GraphOut(nodes=nodes, edges=edges)


@router.get("/orphans", response_model=GraphOut)
def get_orphans(db: Session = Depends(get_db)):
    """Saved items with zero edges — surfaces the "save now, connect later" backlog."""
    linked_keys: set[tuple[ItemType, uuid.UUID]] = set()
    for edge in db.query(GraphEdge).all():
        linked_keys.add((edge.source_type, edge.source_id))
        linked_keys.add((edge.target_type, edge.target_id))

    saved_paper_ids = {row.item_id for row in db.query(ListItem).filter(ListItem.item_type == ItemType.paper)}
    saved_article_ids = {row.item_id for row in db.query(ListItem).filter(ListItem.item_type == ItemType.article)}

    orphan_paper_ids = saved_paper_ids - {i for (t, i) in linked_keys if t == ItemType.paper}
    orphan_article_ids = saved_article_ids - {i for (t, i) in linked_keys if t == ItemType.article}

    papers = db.query(Paper).filter(Paper.id.in_(orphan_paper_ids)).all() if orphan_paper_ids else []
    articles = db.query(Article).filter(Article.id.in_(orphan_article_ids)).all() if orphan_article_ids else []

    nodes = [
        GraphNode(id=_node_id(ItemType.paper, p.id), item_type=ItemType.paper, item_id=p.id, title=p.title, is_saved=True, is_linked=False)
        for p in papers
    ] + [
        GraphNode(id=_node_id(ItemType.article, a.id), item_type=ItemType.article, item_id=a.id, title=a.title, is_saved=True, is_linked=False)
        for a in articles
    ]
    return GraphOut(nodes=nodes, edges=[])


@router.post("/edges", response_model=GraphEdgeOut)
def create_edge(payload: GraphEdgeIn, db: Session = Depends(get_db)):
    edge = GraphEdge(**payload.model_dump(), edge_type=EdgeType.manual)
    db.add(edge)
    try:
        db.commit()
    except IntegrityError:
        # Same pair already linked manually — treat as idempotent rather
        # than erroring, since the graph UI's connect flow can't tell in
        # advance (its own /graph payload doesn't expose per-pair edges).
        db.rollback()
        existing = (
            db.query(GraphEdge)
            .filter(
                GraphEdge.source_type == payload.source_type,
                GraphEdge.source_id == payload.source_id,
                GraphEdge.target_type == payload.target_type,
                GraphEdge.target_id == payload.target_id,
                GraphEdge.edge_type == EdgeType.manual,
            )
            .first()
        )
        if not existing:
            raise
        return existing
    db.refresh(edge)
    return edge


@router.delete("/edges/{edge_id}", status_code=204)
def delete_edge(edge_id: uuid.UUID, db: Session = Depends(get_db)):
    edge = db.get(GraphEdge, edge_id)
    if not edge:
        raise HTTPException(404, "Edge not found")
    db.delete(edge)
    db.commit()
