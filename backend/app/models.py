import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


def _uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now():
    return datetime.now(timezone.utc)


class ItemType(str, enum.Enum):
    paper = "paper"
    article = "article"
    book = "book"
    note = "note"


class SourceKind(str, enum.Enum):
    academic_api = "academic_api"
    rss = "rss"


class SourceTrack(str, enum.Enum):
    research = "research"
    journalism = "journalism"


class Cadence(str, enum.Enum):
    realtime = "realtime"
    daily = "daily"
    weekly = "weekly"


class ReadingState(str, enum.Enum):
    unread = "unread"
    read = "read"
    skimmed = "skimmed"


class EdgeType(str, enum.Enum):
    manual = "manual"
    citation = "citation"


class PaperOrigin(str, enum.Enum):
    source = "source"  # from one of the user's own added Sources
    discovered = "discovered"  # from the broader API set (arXiv/PubMed/OpenAlex/...)
    uploaded = "uploaded"  # user-uploaded PDF — see services/upload.py


class Source(Base):
    """A journal/RSS/site the user has added, or a curated journalism source.

    Searched before the broader API set for any topic that matches its field
    (see services/aggregator.py) — priority breaks ties among user sources.
    """

    __tablename__ = "sources"

    id = _uuid_pk()
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    kind = Column(Enum(SourceKind, name="source_kind"), nullable=False, default=SourceKind.rss)
    track = Column(Enum(SourceTrack, name="source_track"), nullable=False, default=SourceTrack.research)
    field = Column(String, nullable=True)
    is_user_added = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class Topic(Base):
    """A saved plain-language interest with its LLM-translated query and refresh cadence —
    or, when researcher_id is set, a followed person: refreshing pulls their latest works
    from OpenAlex instead of re-running a keyword search (see services/scheduler.py)."""

    __tablename__ = "topics"

    id = _uuid_pk()
    raw_query = Column(String, nullable=False)
    translated_query = Column(String, nullable=True)
    field = Column(String, nullable=True)
    cadence = Column(Enum(Cadence, name="cadence"), default=Cadence.daily, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    researcher_id = Column(UUID(as_uuid=True), ForeignKey("researchers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class Researcher(Base):
    __tablename__ = "researchers"

    id = _uuid_pk()
    name = Column(String, nullable=False)
    orcid = Column(String, nullable=True, unique=True)
    openalex_id = Column(String, nullable=True, unique=True)
    affiliation = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    email = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    faculty_page_url = Column(String, nullable=True)
    # Other OpenAlex author ids that OpenAlex's own disambiguation split off
    # from this same person (fragmented duplicate profiles — see
    # services/sources/openalex.py:search_authors) — kept so ongoing
    # scheduled refresh (services/scheduler.py) keeps pulling works from all
    # of them, not just the one id picked at follow time.
    merged_openalex_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class Paper(Base):
    __tablename__ = "papers"

    id = _uuid_pk()
    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    doi = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True)
    field = Column(String, nullable=True)
    venue = Column(String, nullable=True)
    published_date = Column(DateTime(timezone=True), nullable=True)
    origin_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)
    origin = Column(Enum(PaperOrigin, name="paper_origin"), default=PaperOrigin.discovered, nullable=False)
    oa_status = Column(Boolean, default=False, nullable=False)
    oa_url = Column(String, nullable=True)
    landing_url = Column(String, nullable=True)
    openalex_id = Column(String, nullable=True, unique=True)
    raw_metadata = Column(JSON, nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    # Extracted from the OA PDF on first request and cached — see
    # services/fulltext.py. NULL means "not attempted yet", distinct from ""
    # which would mean "tried, nothing extractable" (we never store that;
    # a failed attempt just leaves this NULL so it retries next time).
    full_text = Column(Text, nullable=True)
    # "Remove" in the feed — hides the paper without deleting it, since it's
    # still a real Paper other things (lists, notes, the graph) can point at.
    # A topic's "reset" clears this back to False for every paper under it.
    dismissed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    origin_source = relationship("Source")
    authors = relationship("PaperAuthor", back_populates="paper", cascade="all, delete-orphan")


class PaperAuthor(Base):
    __tablename__ = "paper_authors"

    id = _uuid_pk()
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    researcher_id = Column(UUID(as_uuid=True), ForeignKey("researchers.id"), nullable=False)
    author_order = Column(Integer, default=0, nullable=False)
    is_corresponding = Column(Boolean, default=False, nullable=False)

    paper = relationship("Paper", back_populates="authors")
    researcher = relationship("Researcher")

    __table_args__ = (UniqueConstraint("paper_id", "researcher_id", name="uq_paper_researcher"),)


class Article(Base):
    """A science-journalism item (Aeon, Quanta, Nature News, curated RSS, etc.)."""

    __tablename__ = "articles"

    id = _uuid_pk()
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    author_name = Column(String, nullable=True)
    # Best-effort link from a byline string to a Researcher row, so a
    # journalism author's name can point somewhere (see
    # services/aggregator.py::_get_or_create_journalist) — matched by exact
    # name, not ORCID/OpenAlex like paper authors, since an RSS byline is
    # just a string with no external id to disambiguate it. NULL for
    # articles ingested before this existed, or with no byline at all.
    author_researcher_id = Column(UUID(as_uuid=True), ForeignKey("researchers.id", ondelete="SET NULL"), nullable=True)
    origin_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)
    is_from_user_source = Column(Boolean, default=False, nullable=False)
    published_date = Column(DateTime(timezone=True), nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    full_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    origin_source = relationship("Source")
    author_researcher = relationship("Researcher")


class Book(Base):
    """A book reference pulled from Open Library — no full text, just discovery/citation."""

    __tablename__ = "books"

    id = _uuid_pk()
    title = Column(Text, nullable=False)
    authors = Column(JSON, nullable=True)  # list[str]; Open Library gives plain names, not ORCID-linked
    first_publish_year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    cover_url = Column(String, nullable=True)
    open_library_id = Column(String, nullable=True, unique=True)
    open_library_url = Column(String, nullable=True)
    field = Column(String, nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class ReadingStatus(Base):
    """Per-item unread/read/skimmed state plus queue (linear) vs reference (library) flags."""

    __tablename__ = "reading_status"

    id = _uuid_pk()
    item_type = Column(Enum(ItemType, name="item_type"), nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(Enum(ReadingState, name="reading_state"), default=ReadingState.unread, nullable=False)
    in_queue = Column(Boolean, default=False, nullable=False)
    in_reference = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (UniqueConstraint("item_type", "item_id", name="uq_reading_status_item"),)


class List(Base):
    __tablename__ = "lists"

    id = _uuid_pk()
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    items = relationship("ListItem", back_populates="list", cascade="all, delete-orphan")


class ListItem(Base):
    __tablename__ = "list_items"

    id = _uuid_pk()
    list_id = Column(UUID(as_uuid=True), ForeignKey("lists.id"), nullable=False)
    item_type = Column(Enum(ItemType, name="item_type"), nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)
    added_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    list = relationship("List", back_populates="items")

    __table_args__ = (UniqueConstraint("list_id", "item_type", "item_id", name="uq_list_item"),)


class Note(Base):
    """A highlight/annotation on a paper/article/book, or a free-standing note
    (item_type/item_id null) written in the split-view Notes pane — an open
    synthesis space that isn't anchored to any single document."""

    __tablename__ = "notes"

    id = _uuid_pk()
    item_type = Column(Enum(ItemType, name="item_type"), nullable=True)
    item_id = Column(UUID(as_uuid=True), nullable=True)
    quote_text = Column(Text, nullable=True)
    note_text = Column(Text, nullable=False)
    topic_tag = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class GraphEdge(Base):
    """A manual (user-drawn) or citation (OpenAlex-derived) connection between two items."""

    __tablename__ = "graph_edges"

    id = _uuid_pk()
    source_type = Column(Enum(ItemType, name="item_type"), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    target_type = Column(Enum(ItemType, name="item_type"), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    edge_type = Column(Enum(EdgeType, name="edge_type"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_type", "source_id", "target_type", "target_id", "edge_type", name="uq_edge"
        ),
    )


class SeenLog(Base):
    """When the user last viewed a topic's feed — drives the "new since last visit" badge."""

    __tablename__ = "seen_log"

    id = _uuid_pk()
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, unique=True)
    last_seen_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class AppSettings(Base):
    """User-editable API keys/config (Settings page) — a single row, since this
    is a single-user app. Overlays app/config.py's .env-derived defaults (see
    services/settings_store.py) rather than replacing them, so a fresh install
    with no keys entered yet still runs on whatever's in .env."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    anthropic_api_key = Column(String, nullable=True)
    unpaywall_email = Column(String, nullable=True)
    openalex_mailto = Column(String, nullable=True)
    ncbi_api_key = Column(String, nullable=True)
    semantic_scholar_api_key = Column(String, nullable=True)
    core_api_key = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
