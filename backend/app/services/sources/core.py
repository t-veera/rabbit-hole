"""CORE.ac.uk API — aggregates institutional-repository copies that Unpaywall
and OpenAlex sometimes miss (e.g. an author's own university repository
mirror that was never indexed elsewhere). Requires a free API key — CORE's
API sits behind Cloudflare for unauthenticated requests (confirmed: a bare
request gets a JS-challenge redirect page, not a 401), so there's no
keyless path here, unlike arXiv/OpenAlex/Unpaywall/PubMed. Silently no-ops
without CORE_API_KEY configured rather than failing the whole lookup chain.
"""

import httpx

from app.services.settings_store import effective_settings

_BASE_URL = "https://api.core.ac.uk/v3/search/works"


def find_pdf_urls(doi: str) -> list[str]:
    settings = effective_settings()
    if not settings.core_api_key:
        return []

    try:
        resp = httpx.get(
            _BASE_URL,
            params={"q": f'doi:"{doi}"'},
            headers={"Authorization": f"Bearer {settings.core_api_key}"},
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except (httpx.HTTPError, ValueError):
        return []

    urls = []
    for result in results:
        pdf_url = result.get("downloadUrl") or result.get("sourceFulltextUrls", [None])[0]
        if pdf_url and pdf_url not in urls:
            urls.append(pdf_url)
    return urls
