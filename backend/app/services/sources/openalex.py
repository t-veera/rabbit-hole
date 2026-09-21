"""OpenAlex REST API — no key required, "polite pool" via mailto param.

https://docs.openalex.org/
Used both for general cross-field paper search and for researcher profile
data (author list, affiliation, ORCID, publication history, citations) —
including searching for a person by name and pulling their full works list
to follow, same as following a topic.
"""

import unicodedata
from datetime import datetime

import httpx

from app.config import get_settings
from app.services.sources.base import NormalizedPaper

_BASE_URL = "https://api.openalex.org"


def _mailto_params() -> dict:
    settings = get_settings()
    return {"mailto": settings.openalex_mailto} if settings.openalex_mailto else {}


def _parse_work(work: dict) -> NormalizedPaper:
    published_date = None
    if work.get("publication_date"):
        try:
            published_date = datetime.fromisoformat(work["publication_date"])
        except ValueError:
            pass

    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        institutions = authorship.get("institutions", [])
        authors.append(
            {
                "name": author.get("display_name", ""),
                "orcid": (author.get("orcid") or "").replace("https://orcid.org/", "") or None,
                "affiliation": institutions[0]["display_name"] if institutions else None,
                "openalex_id": author.get("id"),
            }
        )

    oa = work.get("open_access", {}) or {}
    primary_location = work.get("primary_location", {}) or {}
    return NormalizedPaper(
        title=work.get("title") or work.get("display_name") or "(untitled)",
        abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
        doi=(work.get("doi") or "").replace("https://doi.org/", "") or None,
        external_id=work.get("id"),
        venue=(work.get("primary_location", {}) or {}).get("source", {}).get("display_name")
        if primary_location.get("source")
        else None,
        published_date=published_date,
        landing_url=primary_location.get("landing_page_url") or work.get("id"),
        oa_url=oa.get("oa_url"),
        oa_status=bool(oa.get("is_oa")),
        openalex_id=work.get("id"),
        authors=authors,
        raw_metadata={"source": "openalex"},
    )


def search(query: str, per_page: int = 20) -> list[NormalizedPaper]:
    # No explicit `sort`: OpenAlex defaults to relevance_score:desc whenever
    # `search` is set. Sorting by date instead (as this did before) meant we
    # kept the 20 *newest* loose keyword matches regardless of how well they
    # actually matched — for a query like a multi-word plain-language phrase,
    # that surfaces whatever obscure preprint happened to be uploaded most
    # recently, not what's actually relevant.
    params = {"search": query, "per-page": per_page, **_mailto_params()}
    try:
        resp = httpx.get(f"{_BASE_URL}/works", params=params, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []
    return [_parse_work(w) for w in resp.json().get("results", [])]


def get_work_by_doi(doi: str) -> NormalizedPaper | None:
    """Direct DOI lookup — used to enrich manually uploaded papers that have a
    DOI: gets us their openalex_id (and thus citation edges) without a search."""
    try:
        resp = httpx.get(f"{_BASE_URL}/works/doi:{doi}", params=_mailto_params(), timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    return _parse_work(resp.json())


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]} to dodge copyright issues."""
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


#  Non-ASCII dash/apostrophe variants (curly quotes, the Unicode HYPHEN as
# opposed to hyphen-minus, etc.) must become a plain space *before* the
# ascii-encode step below, not after: encode("ascii", "ignore") drops a
# character like U+2010 entirely rather than mapping it to "-", so
# "Ben‐Ghiat" and "Ben-Ghiat" would otherwise survive that step as
# "BenGhiat" vs "Ben-Ghiat" — still mismatched.
_PUNCT_TO_SPACE = "‐‑‒–—―−‘’“”'-.·"


def _normalize_name(name: str) -> str:
    """Collapses case/punctuation/accent variants of the same name so OpenAlex's
    disambiguation fragments (see search_authors) group together: "RUTH
    BEN-GHIAT", "Ruth Ben‐Ghiat" (Unicode hyphen), "Ruth Ben Ghiat" all
    normalize the same."""
    translated = "".join(" " if ch in _PUNCT_TO_SPACE else ch for ch in name)
    stripped = unicodedata.normalize("NFKD", translated).encode("ascii", "ignore").decode("ascii")
    return " ".join(stripped.lower().split())


def search_authors(name: str, limit: int = 10) -> list[dict]:
    """Search for a person by name — returns candidates to follow, not yet persisted.

    OpenAlex's own author disambiguation frequently splits one real person
    into several author records: a complete profile (real affiliation, full
    works count) plus a handful of near-empty stubs (no affiliation, 1 work)
    that are disambiguation misses, not distinct people. Left unmerged, the
    same person shows up as several separate rows each with its own Follow
    button. Since OpenAlex's `/authors/search` returns them all under the
    same or near-identical display_name, grouping by normalized name and
    keeping the fullest profile as canonical (folding the rest in as
    `merged_ids` so a later follow can still pull their works too) collapses
    that back into one row per actual person.
    """
    params = {"search": name, "per-page": max(limit * 3, limit), **_mailto_params()}
    # One retry before giving up — a transient OpenAlex timeout/5xx used to be
    # swallowed into an empty list here, which looked identical to "no one by
    # this name exists" on the People tab. Surfacing the failure instead (after
    # a single retry) lets the caller tell the two apart.
    resp = None
    last_error: httpx.HTTPError | None = None
    for attempt in range(2):
        try:
            resp = httpx.get(f"{_BASE_URL}/authors", params=params, timeout=15)
            resp.raise_for_status()
            last_error = None
            break
        except httpx.HTTPError as exc:
            last_error = exc
    if last_error is not None or resp is None:
        raise last_error or RuntimeError("OpenAlex author search failed")

    parsed = []
    for author in resp.json().get("results", []):
        institutions = author.get("last_known_institutions") or []
        affiliation = institutions[0].get("display_name") if institutions else None
        parsed.append(
            {
                "openalex_id": author.get("id"),
                "name": author.get("display_name"),
                "orcid": (author.get("orcid") or "").replace("https://orcid.org/", "") or None,
                "affiliation": affiliation,
                "works_count": author.get("works_count") or 0,
            }
        )

    groups: dict[str, list[dict]] = {}
    for candidate in parsed:
        key = _normalize_name(candidate["name"] or "")
        groups.setdefault(key, []).append(candidate)

    merged = []
    for group in groups.values():
        group.sort(key=lambda c: (c["works_count"], bool(c["affiliation"]), bool(c["orcid"])), reverse=True)
        canonical, *duplicates = group
        merged.append(
            {
                "openalex_id": canonical["openalex_id"],
                "name": canonical["name"],
                "orcid": canonical["orcid"] or next((d["orcid"] for d in duplicates if d["orcid"]), None),
                "affiliation": canonical["affiliation"],
                "works_count": sum(c["works_count"] for c in group) or None,
                "merged_ids": [d["openalex_id"] for d in duplicates],
            }
        )

    merged.sort(key=lambda c: c["works_count"] or 0, reverse=True)
    return merged[:limit]


def get_author(openalex_id: str) -> dict | None:
    try:
        resp = httpx.get(f"{_BASE_URL}/authors/{openalex_id}", params=_mailto_params(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return None


def get_author_works(openalex_id: str, per_page: int = 25) -> list[NormalizedPaper]:
    """Full records (abstract, authors, OA links) for everything this person has written —
    used both to display a profile's publication list and to ingest+follow them like a topic."""
    params = {
        "filter": f"author.id:{openalex_id}",
        "sort": "publication_date:desc",
        "per-page": per_page,
        **_mailto_params(),
    }
    try:
        resp = httpx.get(f"{_BASE_URL}/works", params=params, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []
    return [_parse_work(w) for w in resp.json().get("results", [])]


def get_work_citations(openalex_id: str) -> dict:
    """Returns {"cites": [openalex_ids], "cited_by": [openalex_ids]} for a work."""
    try:
        resp = httpx.get(openalex_id if openalex_id.startswith("http") else f"{_BASE_URL}/works/{openalex_id}",
                          params=_mailto_params(), timeout=15)
        resp.raise_for_status()
        work = resp.json()
    except httpx.HTTPError:
        return {"cites": [], "cited_by": []}

    cites = work.get("referenced_works", []) or []

    cited_by: list[str] = []
    cited_by_url = work.get("cited_by_api_url")
    if cited_by_url:
        try:
            resp2 = httpx.get(cited_by_url, params={**_mailto_params(), "per-page": 50}, timeout=15)
            resp2.raise_for_status()
            cited_by = [w["id"] for w in resp2.json().get("results", [])]
        except httpx.HTTPError:
            pass

    return {"cites": cites, "cited_by": cited_by}
