"""bioRxiv / medRxiv public API — no key required.

https://api.biorxiv.org/ has no free-text search endpoint, only a details
listing by date interval. We fetch a recent window and filter client-side
by keyword match against title/abstract — a real limitation of the
upstream API, not a shortcut we're taking.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import httpx

from app.services.sources.base import NormalizedPaper

_BASE_URL = "https://api.biorxiv.org/details"
_WINDOW_DAYS = 30
_PAGE_SIZE = 100
_MAX_PAGES = 3  # each page is 100 records; caps worst-case latency


def _fetch_page(server: str, start, end, cursor: int) -> list[dict]:
    url = f"{_BASE_URL}/{server}/{start.isoformat()}/{end.isoformat()}/{cursor}"
    try:
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json().get("collection", [])
    except (httpx.HTTPError, ValueError):
        return []


def _to_papers(server: str, collection: list[dict], terms: list[str]) -> list[NormalizedPaper]:
    papers = []
    for item in collection:
        haystack = f"{item.get('title', '')} {item.get('abstract', '')}".lower()
        if terms and not any(t in haystack for t in terms):
            continue
        authors = [{"name": n.strip()} for n in (item.get("authors") or "").split(";") if n.strip()]
        published_date = None
        if item.get("date"):
            try:
                published_date = datetime.fromisoformat(item["date"])
            except ValueError:
                pass
        doi = item.get("doi")
        papers.append(
            NormalizedPaper(
                title=item.get("title", "").strip(),
                abstract=item.get("abstract"),
                doi=doi,
                external_id=f"{server}:{doi}" if doi else None,
                venue=server,
                published_date=published_date,
                landing_url=f"https://doi.org/{doi}" if doi else None,
                oa_url=f"https://www.{server}.org/content/{doi}v{item.get('version', '1')}.full.pdf" if doi else None,
                oa_status=True,
                openalex_id=None,
                authors=authors,
                raw_metadata={"source": server, "category": item.get("category")},
            )
        )
    return papers


def _search(server: str, query: str, max_results: int) -> list[NormalizedPaper]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=_WINDOW_DAYS)
    terms = [t.lower() for t in query.split() if len(t) > 2]

    # Page 1 alone satisfies most queries — fetch it by itself first so the
    # common case pays for exactly one round-trip. Only fan out to the
    # remaining pages (concurrently, since their cursors don't depend on
    # page 1's content) when that's not enough; this upstream API's later
    # pages have been observed to be far slower/less reliable than page 1
    # (confirmed: page 2 timed out entirely in testing), so this also keeps
    # that cost off the common path instead of paying it on every search.
    first_page = _fetch_page(server, start, end, 0)
    results = _to_papers(server, first_page, terms)
    if len(results) >= max_results or len(first_page) < _PAGE_SIZE:
        return results[:max_results]

    with ThreadPoolExecutor(max_workers=_MAX_PAGES - 1) as executor:
        later_pages = list(
            executor.map(lambda i: _fetch_page(server, start, end, i * _PAGE_SIZE), range(1, _MAX_PAGES))
        )
    for collection in later_pages:
        results.extend(_to_papers(server, collection, terms))
        if len(results) >= max_results:
            break

    return results[:max_results]


def search_biorxiv(query: str, max_results: int = 20) -> list[NormalizedPaper]:
    return _search("biorxiv", query, max_results)


def search_medrxiv(query: str, max_results: int = 20) -> list[NormalizedPaper]:
    return _search("medrxiv", query, max_results)
