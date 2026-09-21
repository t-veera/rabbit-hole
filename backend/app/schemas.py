import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import Cadence, EdgeType, ItemType, PaperOrigin, ReadingState, SourceKind, SourceTrack


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Sources ---


class SourceIn(BaseModel):
    name: str
    url: str
    kind: SourceKind = SourceKind.rss
    track: SourceTrack = SourceTrack.research
    field: str | None = None
    priority: int = 0

    @field_validator("url")
    @classmethod
    def _url_looks_valid(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v


class SourceOut(ORMBase):
    id: uuid.UUID
    name: str
    url: str
    kind: SourceKind
    track: SourceTrack
    field: str | None
    is_user_added: bool
    priority: int
    created_at: datetime


# --- Topics ---


class TopicIn(BaseModel):
    raw_query: str
    field: str | None = None
    cadence: Cadence = Cadence.daily


class TopicPatch(BaseModel):
    cadence: Cadence | None = None
    field: str | None = None


class TopicOut(ORMBase):
    id: uuid.UUID
    raw_query: str
    translated_query: str | None
    field: str | None
    cadence: Cadence
    last_run_at: datetime | None
    researcher_id: uuid.UUID | None
    created_at: datetime


class TranslateRequest(BaseModel):
    raw_query: str


class TranslateResponse(BaseModel):
    raw_query: str
    translated_query: str
    inferred_field: str


# --- Researchers ---


class ResearcherOut(ORMBase):
    id: uuid.UUID
    name: str
    orcid: str | None
    openalex_id: str | None
    affiliation: str | None
    degree: str | None
    email: str | None
    photo_url: str | None
    faculty_page_url: str | None


class AuthorSearchResult(BaseModel):
    openalex_id: str
    name: str
    orcid: str | None
    affiliation: str | None
    works_count: int | None
    merged_ids: list[str] = []


class FollowResearcherRequest(BaseModel):
    openalex_id: str
    cadence: Cadence = Cadence.daily
    merged_ids: list[str] = []


class FollowResearcherResponse(BaseModel):
    researcher: ResearcherOut
    topic: TopicOut
    papers_found: int


class PaperAuthorOut(BaseModel):
    author_order: int
    is_corresponding: bool
    researcher: ResearcherOut

    model_config = ConfigDict(from_attributes=True)


# --- Reading status ---


class ReadingStatusOut(ORMBase):
    item_type: ItemType
    item_id: uuid.UUID
    status: ReadingState
    in_queue: bool
    in_reference: bool
    updated_at: datetime


class ReadingStatusPatch(BaseModel):
    status: ReadingState | None = None
    in_queue: bool | None = None
    in_reference: bool | None = None


# --- Papers / Articles ---


class PaperOut(ORMBase):
    id: uuid.UUID
    title: str
    abstract: str | None
    doi: str | None
    external_id: str | None
    field: str | None
    venue: str | None
    published_date: datetime | None
    origin: PaperOrigin
    oa_status: bool
    oa_url: str | None
    landing_url: str | None
    openalex_id: str | None
    created_at: datetime
    origin_source: SourceOut | None = None
    authors: list[PaperAuthorOut] = []
    reading_status: ReadingStatusOut | None = None


class ArticleOut(ORMBase):
    id: uuid.UUID
    title: str
    summary: str | None
    url: str
    author_name: str | None
    author_researcher_id: uuid.UUID | None
    is_from_user_source: bool
    published_date: datetime | None
    created_at: datetime
    origin_source: SourceOut | None = None
    reading_status: ReadingStatusOut | None = None


class BookOut(ORMBase):
    id: uuid.UUID
    title: str
    authors: list[str] | None
    first_publish_year: int | None
    isbn: str | None
    description: str | None
    cover_url: str | None
    open_library_id: str | None
    open_library_url: str | None
    created_at: datetime
    reading_status: ReadingStatusOut | None = None


class UploadDraft(BaseModel):
    """What we could extract from the PDF itself — the user reviews/fills gaps before confirming.
    No server-side temp storage: the frontend holds this and resubmits it (edited) to confirm."""

    suggested_title: str | None
    suggested_authors: list[str]
    suggested_doi: str | None
    full_text: str
    page_count: int


class UploadConfirmRequest(BaseModel):
    title: str
    authors: list[str]
    published_date: datetime | None = None
    venue: str | None = None
    doi: str | None = None
    full_text: str


class SearchRunRequest(BaseModel):
    raw_query: str
    field: str | None = None
    save_as_topic: bool = False
    cadence: Cadence = Cadence.daily


class SearchRunResponse(BaseModel):
    translated_query: str
    inferred_field: str
    papers: list[PaperOut]
    articles: list[ArticleOut]
    books: list[BookOut] = []
    topic_id: uuid.UUID | None = None


# --- Lists ---


class ListIn(BaseModel):
    name: str


class ListOut(ORMBase):
    id: uuid.UUID
    name: str
    created_at: datetime


class ListItemIn(BaseModel):
    item_type: ItemType
    item_id: uuid.UUID


class ListItemOut(ORMBase):
    id: uuid.UUID
    item_type: ItemType
    item_id: uuid.UUID
    added_at: datetime


# --- Notes ---


class NoteIn(BaseModel):
    item_type: ItemType | None = None
    item_id: uuid.UUID | None = None
    quote_text: str | None = None
    note_text: str
    topic_tag: str | None = None


class NotePatch(BaseModel):
    note_text: str | None = None
    quote_text: str | None = None
    topic_tag: str | None = None


class NoteOut(ORMBase):
    id: uuid.UUID
    item_type: ItemType | None
    item_id: uuid.UUID | None
    quote_text: str | None
    note_text: str
    topic_tag: str | None
    created_at: datetime


# --- Graph ---


class GraphEdgeIn(BaseModel):
    source_type: ItemType
    source_id: uuid.UUID
    target_type: ItemType
    target_id: uuid.UUID


class GraphEdgeOut(ORMBase):
    id: uuid.UUID
    source_type: ItemType
    source_id: uuid.UUID
    target_type: ItemType
    target_id: uuid.UUID
    edge_type: EdgeType
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    item_type: ItemType
    item_id: uuid.UUID
    title: str
    is_saved: bool
    is_linked: bool


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdgeOut]


# --- Notifications ---


# --- App settings (Settings page API keys) ---


class AppSettingsIn(BaseModel):
    """All optional and unset-vs-empty-string aware (see routers/settings.py):
    a field left out of the request body leaves that key untouched; an empty
    string clears it back to whatever's in .env."""

    anthropic_api_key: str | None = None
    unpaywall_email: str | None = None
    openalex_mailto: str | None = None
    ncbi_api_key: str | None = None
    semantic_scholar_api_key: str | None = None
    core_api_key: str | None = None


class AppSettingsOut(BaseModel):
    """Secrets are never echoed back in full once saved — only whether one is
    set, and whether it's coming from this app's Settings page or from
    .env/the environment. unpaywall_email/openalex_mailto aren't secrets
    (just contact addresses Unpaywall/OpenAlex ask for), so those show in
    full — the user needs to see them to edit them."""

    anthropic_api_key_set: bool
    anthropic_api_key_source: str
    unpaywall_email: str
    unpaywall_email_source: str
    openalex_mailto: str | None
    openalex_mailto_source: str
    ncbi_api_key_set: bool
    ncbi_api_key_source: str
    semantic_scholar_api_key_set: bool
    semantic_scholar_api_key_source: str
    core_api_key_set: bool
    core_api_key_source: str


class NotificationOut(BaseModel):
    topic_id: uuid.UUID
    topic_query: str
    new_count: int
