"""Open Library search API — free, no auth, no signup.

https://openlibrary.org/dev/docs/api/search
Used to bring books into results alongside papers and journalism, since a
plain-language interest (e.g. paleoanthropology) is often better served by
a book than by another preprint.
"""

import httpx

_BASE_URL = "https://openlibrary.org/search.json"
_COVERS_URL = "https://covers.openlibrary.org/b/id"


def search(query: str, limit: int = 10) -> list[dict]:
    params = {
        "q": query,
        "limit": limit,
        "fields": "key,title,author_name,first_publish_year,isbn,cover_i,first_sentence",
    }
    try:
        resp = httpx.get(_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except (httpx.HTTPError, ValueError):
        return []

    results = []
    for doc in docs:
        work_key = doc.get("key")  # e.g. "/works/OL12345W"
        cover_id = doc.get("cover_i")
        first_sentence = doc.get("first_sentence")
        if isinstance(first_sentence, list):
            first_sentence = first_sentence[0] if first_sentence else None

        results.append(
            {
                "title": doc.get("title") or "(untitled)",
                "authors": doc.get("author_name") or [],
                "first_publish_year": doc.get("first_publish_year"),
                "isbn": (doc.get("isbn") or [None])[0],
                "description": first_sentence,
                "cover_url": f"{_COVERS_URL}/{cover_id}-M.jpg" if cover_id else None,
                "open_library_id": work_key,
                "open_library_url": f"https://openlibrary.org{work_key}" if work_key else None,
            }
        )
    return results
