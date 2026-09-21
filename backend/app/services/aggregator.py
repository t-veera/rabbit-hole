"""Orchestrates a topic search: translate -> route -> fetch -> persist.

Search order (per spec, critical): the user's own added Sources matching
the inferred field are searched first and tagged origin=source, then the
broader API set (arXiv/PubMed/bioRxiv/OpenAlex) fills in the rest as
origin=discovered. Manually uploaded PDFs (see services/upload.py) get
origin=uploaded and go through this same _upsert_paper path.
"""

import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.field_routing import sources_for_field
from app.models import Article, Book, Paper, PaperAuthor, PaperOrigin, Researcher, Source, SourceKind, SourceTrack
from app.services.sources import arxiv, biorxiv, openalex, openlibrary, pubmed, rss, unpaywall
from app.services.sources.base import NormalizedPaper

_SOURCE_MODULES = {
    "arxiv": arxiv.search,
    "pubmed": pubmed.search,
    "biorxiv": biorxiv.search_biorxiv,
    "medrxiv": biorxiv.search_medrxiv,
    "openalex": openalex.search,
}

# Same minimal stopword list the naive translator uses (services/llm.py) —
# duplicated rather than imported to keep this module's relevance filter
# independent of translation internals.
_STOPWORDS = {"the", "a", "an", "and", "of", "in", "on", "about", "for", "to", "is", "are"}
# A real person-name match must clear this works_count bar before its papers
# get pulled in — filters out disambiguation-stub authors (1-2 works) that
# happen to share a word with the query.
_PERSON_MATCH_MIN_WORKS = 5


def _query_terms(query: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9']+", query.lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def _is_relevant(record: dict, terms: set[str]) -> bool:
    """Relevance floor: a keyword-searched result must share at least one
    meaningful term with the query, or it gets dropped rather than padded
    into the result count. Doesn't apply to user's own RSS sources (they
    opted into that feed on purpose) or to author-identity-driven results
    (see _resolve_person) — those are relevant by authorship, not text match.
    """
    if not terms:
        return True
    haystack = f"{record.get('title') or ''} {record.get('abstract') or ''}".lower()
    haystack_terms = set(re.findall(r"[a-zA-Z0-9']+", haystack))
    return bool(terms & haystack_terms)


def _resolve_person(raw_query: str) -> dict | None:
    """If the query is naming a real person (a name mixed in with topic
    words, in any casing — search boxes get typed lowercase), find them via
    OpenAlex author search so their actual work can be weighted into results
    instead of relying on generic keyword search to surface it.

    Tries contiguous 2- and 3-word windows of the query (bounded to keep the
    extra API calls cheap) and keeps the best confident match, so "ruth
    ben-ghiat politics" resolves the "ruth ben-ghiat" window to the real
    person rather than being diluted into an unfocused 3-word topic search.
    """
    tokens = raw_query.split()
    if not (2 <= len(tokens) <= 6):
        return None

    windows = []
    for size in (2, 3):
        for i in range(len(tokens) - size + 1):
            windows.append(" ".join(tokens[i : i + size]))

    def _lookup(window: str) -> dict | None:
        try:
            candidates = openalex.search_authors(window, limit=1)
        except Exception:
            return None
        return candidates[0] if candidates else None

    best: dict | None = None
    # These windows are independent lookups against the same read-only API —
    # run them concurrently rather than one network round-trip at a time,
    # since a 6-word query fans out to up to 9 of these per search.
    with ThreadPoolExecutor(max_workers=min(len(windows), 9) or 1) as executor:
        for top in executor.map(_lookup, windows):
            if not top:
                continue
            if (top.get("works_count") or 0) < _PERSON_MATCH_MIN_WORKS:
                continue
            if best is None or (top.get("works_count") or 0) > (best.get("works_count") or 0):
                best = top
    return best


def run_search(db: Session, translated_query: str, field: str, topic_id: uuid.UUID | None = None, raw_query: str | None = None) -> dict:
    """Fetches + persists papers and articles for a translated query. Returns {"papers": [...], "articles": [...]}."""

    user_sources = (
        db.query(Source)
        .filter(Source.is_user_added.is_(True), Source.track == SourceTrack.research)
        .filter((Source.field == field) | (Source.field.is_(None)))
        .order_by(Source.priority)
        .all()
    )

    saved_papers: list[Paper] = []
    seen_doi_or_ext: set[str] = set()

    for source in user_sources:
        if source.kind != SourceKind.rss:
            continue
        normalized = rss.fetch_as_papers(source.url, query=translated_query)
        for record in normalized:
            paper = _upsert_paper(db, record, topic_id, origin=PaperOrigin.source, origin_source_id=source.id)
            key = record.get("doi") or record.get("external_id") or record.get("title")
            if key and key not in seen_doi_or_ext:
                seen_doi_or_ext.add(key)
                saved_papers.append(paper)

    # Person-aware boost: if the query names a real, identifiable person,
    # pull their actual work in directly (by authorship, not keyword luck)
    # and put it first — this is the part generic keyword search can't do
    # reliably, especially once a name is diluted into a broad topic query.
    person_papers: list[Paper] = []
    if raw_query:
        person = _resolve_person(raw_query)
        if person and person.get("openalex_id"):
            for author_id in [person["openalex_id"], *(person.get("merged_ids") or [])]:
                for record in openalex.get_author_works(author_id, per_page=15):
                    key = record.get("doi") or record.get("external_id") or record.get("title")
                    if key in seen_doi_or_ext:
                        continue
                    seen_doi_or_ext.add(key)
                    paper = _upsert_paper(db, record, topic_id, origin=PaperOrigin.discovered, origin_source_id=None)
                    person_papers.append(paper)

    query_terms = _query_terms(translated_query)
    fetch_fns = [_SOURCE_MODULES[name] for name in sources_for_field(field) if name in _SOURCE_MODULES]
    discovered_records: list[NormalizedPaper] = []
    if fetch_fns:
        # Independent, read-only fetches against different APIs (arXiv,
        # PubMed, bioRxiv/medRxiv, OpenAlex) — run concurrently instead of
        # one full round-trip at a time. A single source erroring (e.g. a
        # malformed response) shouldn't sink the rest of the search.
        with ThreadPoolExecutor(max_workers=len(fetch_fns)) as executor:
            futures = [executor.submit(fn, translated_query) for fn in fetch_fns]
            for future in as_completed(futures):
                try:
                    discovered_records.extend(future.result())
                except Exception:
                    continue

    # Unpaywall's per-DOI OA check (in _upsert_paper) is the single biggest
    # cost of a search — one blocking HTTP call per unique paper. Resolving
    # every DOI in this batch concurrently up front, then handing each
    # record its already-fetched result, turns that from N sequential
    # round-trips into one wave of parallel ones.
    candidate_dois = {r["doi"] for r in discovered_records if r.get("doi") and r["doi"] not in seen_doi_or_ext}
    oa_lookup: dict[str, dict | None] = {}
    if candidate_dois:
        with ThreadPoolExecutor(max_workers=min(len(candidate_dois), 16)) as executor:
            futures = {executor.submit(unpaywall.check_oa, doi): doi for doi in candidate_dois}
            for future in as_completed(futures):
                doi = futures[future]
                try:
                    oa_lookup[doi] = future.result()
                except Exception:
                    oa_lookup[doi] = None

    for record in discovered_records:
        key = record.get("doi") or record.get("external_id") or record.get("title")
        if key in seen_doi_or_ext:
            continue
        if not _is_relevant(record, query_terms):
            continue
        seen_doi_or_ext.add(key)
        paper = _upsert_paper(db, record, topic_id, origin=PaperOrigin.discovered, origin_source_id=None, oa_lookup=oa_lookup)
        saved_papers.append(paper)

    saved_papers = person_papers + saved_papers

    journalism_articles = _run_journalism(db, translated_query, field, topic_id)
    books = _run_books(db, translated_query, field, topic_id)

    db.commit()
    for paper in saved_papers:
        db.refresh(paper)
    for book in books:
        db.refresh(book)
    return {"papers": saved_papers, "articles": journalism_articles, "books": books}


def ingest_researcher_works(db: Session, researcher: Researcher, topic_id: uuid.UUID) -> list[Paper]:
    """Pulls everything a followed person has written from OpenAlex and upserts
    it as Papers tagged to their follow-topic — same dedup/OA-enrichment path
    as a keyword search, just driven by author id instead of a query string.

    Also pulls from merged_openalex_ids — other OpenAlex author records that
    search_authors() determined were disambiguation duplicates of this same
    person (see services/sources/openalex.py) — so a merged "one person, one
    Follow button" result actually surfaces all of their work, not just
    whichever id happened to be picked as canonical. _upsert_paper already
    dedups by DOI/openalex_id, so overlapping works across ids are harmless.
    """
    if not researcher.openalex_id:
        return []

    saved: list[Paper] = []
    for author_id in [researcher.openalex_id, *(researcher.merged_openalex_ids or [])]:
        for record in openalex.get_author_works(author_id):
            paper = _upsert_paper(db, record, topic_id, origin=PaperOrigin.discovered, origin_source_id=None)
            saved.append(paper)

    db.commit()
    for paper in saved:
        db.refresh(paper)
    return saved


def _run_books(db: Session, translated_query: str, field: str, topic_id: uuid.UUID | None) -> list[Book]:
    saved: list[Book] = []
    for record in openlibrary.search(translated_query, limit=8):
        existing = None
        if record.get("open_library_id"):
            existing = db.query(Book).filter(Book.open_library_id == record["open_library_id"]).first()
        if existing:
            saved.append(existing)
            continue
        book = Book(
            title=record["title"],
            authors=record.get("authors") or [],
            first_publish_year=record.get("first_publish_year"),
            isbn=record.get("isbn"),
            description=record.get("description"),
            cover_url=record.get("cover_url"),
            open_library_id=record.get("open_library_id"),
            open_library_url=record.get("open_library_url"),
            field=field,
            topic_id=topic_id,
        )
        db.add(book)
        saved.append(book)
    return saved


def _get_or_create_journalist(db: Session, name: str, cache: dict[str, Researcher]) -> Researcher:
    """Best-effort link from an RSS byline string to a Researcher row (see
    Article.author_researcher_id) — matched by exact name, case-insensitive.
    No ORCID/OpenAlex id to disambiguate a byline against, unlike paper
    authors, so two different people who happen to share a name will share
    one Researcher row here. Acceptable tradeoff for a single-user app; the
    alternative (no link at all) is strictly worse."""
    key = name.lower()
    if key in cache:
        return cache[key]
    researcher = db.query(Researcher).filter(func.lower(Researcher.name) == key).first()
    if not researcher:
        researcher = Researcher(name=name)
        db.add(researcher)
        db.flush()
    cache[key] = researcher
    return researcher


def _run_journalism(db: Session, translated_query: str, field: str, topic_id: uuid.UUID | None) -> list[Article]:
    sources = (
        db.query(Source)
        .filter(Source.track == SourceTrack.journalism, Source.kind == SourceKind.rss)
        .order_by(Source.priority)
        .all()
    )
    saved: list[Article] = []
    journalist_cache: dict[str, Researcher] = {}

    # Fetching each feed is a blocking network call (feedparser.parse hits
    # the URL itself) — independent per source, so fan them out concurrently
    # rather than one full round-trip at a time before touching the DB.
    fetched: dict[uuid.UUID, list[dict]] = {}
    if sources:
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            futures = {
                executor.submit(rss.fetch, source.url, translated_query, 10): source.id for source in sources
            }
            for future in as_completed(futures):
                source_id = futures[future]
                try:
                    fetched[source_id] = future.result()
                except Exception:
                    fetched[source_id] = []

    for source in sources:
        for item in fetched.get(source.id, []):
            existing = db.query(Article).filter(Article.url == item["url"]).first()
            if existing:
                continue
            author_name = item.get("author_name")
            author_researcher = _get_or_create_journalist(db, author_name, journalist_cache) if author_name else None
            article = Article(
                title=item["title"],
                summary=item["summary"],
                url=item["url"],
                author_name=author_name,
                author_researcher_id=author_researcher.id if author_researcher else None,
                origin_source_id=source.id,
                is_from_user_source=source.is_user_added,
                published_date=item["published_date"],
                topic_id=topic_id,
            )
            db.add(article)
            saved.append(article)
    return saved


def _upsert_paper(
    db: Session,
    record: NormalizedPaper,
    topic_id: uuid.UUID | None,
    origin: PaperOrigin,
    origin_source_id: uuid.UUID | None,
    oa_lookup: dict[str, dict | None] | None = None,
) -> Paper:
    existing = None
    if record.get("doi"):
        existing = db.query(Paper).filter(Paper.doi == record["doi"]).first()
    if not existing and record.get("openalex_id"):
        existing = db.query(Paper).filter(Paper.openalex_id == record["openalex_id"]).first()
    if not existing and record.get("external_id"):
        existing = db.query(Paper).filter(Paper.external_id == record["external_id"]).first()

    if existing:
        # Backfill the topic association rather than silently skipping it:
        # without this, a paper ingested once untagged (e.g. a one-off search
        # with save_as_topic=False) would never pick up a topic_id from a
        # later, more specific ingest — like following a researcher whose
        # work was already in the library — so "View papers" for that
        # topic/follow would undercount even though the papers exist. Only
        # backfills a NULL topic_id; never steals a paper from a topic it's
        # already tagged to.
        if topic_id is not None and existing.topic_id is None:
            existing.topic_id = topic_id
        return existing

    oa_status = record.get("oa_status", False)
    oa_url = record.get("oa_url")
    raw_metadata = dict(record.get("raw_metadata") or {})
    # Always check Unpaywall when we have a DOI, even if the source (e.g.
    # OpenAlex) already claims OA: Unpaywall's best_oa_location often points
    # at a direct PDF (url_for_pdf), while OpenAlex's oa_url is frequently
    # just the DOI landing page — which most publishers/repositories block
    # from being embedded in an iframe (X-Frame-Options), so the direct PDF
    # is what actually makes in-app reading work.
    if record.get("doi"):
        doi = record["doi"]
        oa_info = oa_lookup[doi] if oa_lookup is not None and doi in oa_lookup else unpaywall.check_oa(doi)
        if oa_info:
            oa_status = oa_status or oa_info["is_oa"]
            if oa_info["oa_url"]:
                oa_url = oa_info["oa_url"]
            if oa_info["oa_candidates"]:
                raw_metadata["oa_candidates"] = oa_info["oa_candidates"]

    paper = Paper(
        title=record["title"],
        abstract=record.get("abstract"),
        doi=record.get("doi"),
        external_id=record.get("external_id"),
        field=None,
        venue=record.get("venue"),
        published_date=record.get("published_date"),
        origin_source_id=origin_source_id,
        origin=origin,
        oa_status=oa_status,
        oa_url=oa_url,
        landing_url=record.get("landing_url"),
        openalex_id=record.get("openalex_id"),
        raw_metadata=raw_metadata or None,
        topic_id=topic_id,
    )
    db.add(paper)
    db.flush()

    seen_researcher_ids: set[uuid.UUID] = set()
    for order, author_record in enumerate(record.get("authors", [])):
        researcher = _upsert_researcher(db, author_record)
        if researcher.id in seen_researcher_ids:
            # Some sources (e.g. OpenAlex) occasionally list the same author twice
            # per work; paper_authors has a uniqueness constraint on the pair.
            continue
        seen_researcher_ids.add(researcher.id)
        db.add(
            PaperAuthor(
                paper_id=paper.id,
                researcher_id=researcher.id,
                author_order=order,
                is_corresponding=bool(author_record.get("is_corresponding") or author_record.get("email")),
            )
        )

    return paper


def _upsert_researcher(db: Session, author_record: dict) -> Researcher:
    researcher = None
    if author_record.get("orcid"):
        researcher = db.query(Researcher).filter(Researcher.orcid == author_record["orcid"]).first()
    if not researcher and author_record.get("openalex_id"):
        researcher = db.query(Researcher).filter(Researcher.openalex_id == author_record["openalex_id"]).first()
    if not researcher and author_record.get("name"):
        researcher = db.query(Researcher).filter(Researcher.name == author_record["name"]).first()

    if researcher:
        if author_record.get("affiliation") and not researcher.affiliation:
            researcher.affiliation = author_record["affiliation"]
        if author_record.get("email") and not researcher.email:
            researcher.email = author_record["email"]
        return researcher

    researcher = Researcher(
        name=author_record.get("name") or "Unknown",
        orcid=author_record.get("orcid"),
        openalex_id=author_record.get("openalex_id"),
        affiliation=author_record.get("affiliation"),
        email=author_record.get("email"),
    )
    db.add(researcher)
    db.flush()
    return researcher
