"""In-app full-text reading for journalism articles.

Unlike papers, there's no Unpaywall/PMC/CORE equivalent for news/science
journalism — an Article's `url` (services/sources/rss.py etc.) *is* the only
copy. Fetch that page directly and pull the actual article body out of the
surrounding nav/ads/comments/boilerplate with trafilatura (a maintained
readability-style extractor), rather than leaving the reader with just the
RSS-feed summary and a "go read it on the source site" link.
"""

import httpx
import trafilatura

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_article_fulltext(url: str) -> str | None:
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30, headers=_HEADERS)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    text = trafilatura.extract(
        resp.text,
        url=url,
        favor_recall=True,
        include_comments=False,
        include_tables=True,
        deduplicate=True,
    )
    if not text or len(text) < 200:
        return None
    return text
