"""arXiv Atom API — no key required. https://export.arxiv.org/api_help/"""

from datetime import datetime
from xml.etree import ElementTree

import httpx

from app.services.sources.base import NormalizedPaper

_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_BASE_URL = "https://export.arxiv.org/api/query"


def search(query: str, max_results: int = 20) -> list[NormalizedPaper]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    try:
        resp = httpx.get(_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    root = ElementTree.fromstring(resp.text)
    results: list[NormalizedPaper] = []
    for entry in root.findall("atom:entry", _NS):
        title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip()
        abstract = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip()
        entry_id = entry.findtext("atom:id", default="", namespaces=_NS) or ""
        arxiv_id = entry_id.rsplit("/", 1)[-1]
        published_raw = entry.findtext("atom:published", default="", namespaces=_NS)
        published_date = None
        if published_raw:
            try:
                published_date = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                pass

        pdf_url = None
        for link in entry.findall("atom:link", _NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")

        authors = [
            {"name": (a.findtext("atom:name", default="", namespaces=_NS) or "").strip()}
            for a in entry.findall("atom:author", _NS)
        ]

        results.append(
            NormalizedPaper(
                title=title,
                abstract=abstract,
                doi=entry.findtext("arxiv:doi", default=None, namespaces=_NS),
                external_id=f"arxiv:{arxiv_id}",
                venue="arXiv",
                published_date=published_date,
                landing_url=entry_id,
                oa_url=pdf_url,
                oa_status=True,
                openalex_id=None,
                authors=authors,
                raw_metadata={"source": "arxiv", "arxiv_id": arxiv_id},
            )
        )
    return results
