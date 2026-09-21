"""Generic RSS/Atom fetcher for user-added custom sources and curated journalism feeds.

Used for: Custom Sources (searched first, per-topic), and the Journalism
track (Aeon, Quanta, Nature News, Science News, etc.).
"""

from datetime import datetime, timezone

import feedparser
from bs4 import BeautifulSoup

from app.services.sources.base import NormalizedPaper


def _strip_html(text: str) -> str:
    """Feed <description>/<content:encoded> is frequently HTML (Aeon's, for
    one, embeds a full <img>/<p> markup blob) — feedparser hands that back
    as-is in .summary, so without this it renders as raw tags in the UI
    instead of readable text."""
    if not text or "<" not in text:
        return text
    return BeautifulSoup(text, "html.parser").get_text(separator=" ").strip()


def fetch(feed_url: str, query: str | None = None, max_results: int = 30) -> list[dict]:
    """Returns normalized article dicts: title, summary, url, author_name, published_date.

    If query is given, only entries whose title/summary contain a query
    term are returned (RSS feeds have no server-side search).
    """
    parsed = feedparser.parse(feed_url)
    terms = [t.lower() for t in query.split() if len(t) > 2] if query else []

    results = []
    for entry in parsed.entries[:200]:
        title = _strip_html(entry.get("title", "")).strip()
        summary = _strip_html(entry.get("summary", ""))
        haystack = f"{title} {summary}".lower()
        if terms and not any(t in haystack for t in terms):
            continue

        published_date = None
        if entry.get("published_parsed"):
            published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        results.append(
            {
                "title": title,
                "summary": summary,
                "url": entry.get("link", ""),
                "author_name": entry.get("author"),
                "published_date": published_date,
            }
        )
        if len(results) >= max_results:
            break

    return results


def fetch_as_papers(feed_url: str, query: str | None = None, max_results: int = 30) -> list[NormalizedPaper]:
    """Some user-added custom sources are journal RSS feeds carrying papers, not journalism."""
    items = fetch(feed_url, query, max_results)
    return [
        NormalizedPaper(
            title=item["title"],
            abstract=item["summary"],
            doi=None,
            external_id=None,
            venue=None,
            published_date=item["published_date"],
            landing_url=item["url"],
            oa_url=None,
            oa_status=False,
            openalex_id=None,
            authors=[{"name": item["author_name"]}] if item.get("author_name") else [],
            raw_metadata={"source": "rss"},
        )
        for item in items
    ]
