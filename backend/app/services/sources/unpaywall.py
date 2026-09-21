"""Unpaywall API — free, no auth, but requires an email per their usage terms.

https://unpaywall.org/products/api
Called for every DOI to check for a legal open-access copy before falling
back to publisher-link-only or preprint-server PDF links.

Unpaywall blocklists the literal placeholder "you@example.com" (422 Unprocessable
Entity) — UNPAYWALL_EMAIL in .env must be a real address or every lookup here
fails closed, silently degrading full-text links to whatever OpenAlex has
(usually a DOI landing page, not a direct PDF).
"""

import logging

import httpx

from app.config import get_settings

_BASE_URL = "https://api.unpaywall.org/v2"
_logger = logging.getLogger(__name__)


def check_oa(doi: str) -> dict | None:
    """Returns {"is_oa": bool, "oa_url": str | None, "oa_candidates": list[str]} or None.

    oa_candidates lists *every* OA copy Unpaywall knows about, not just its
    single "best" pick — sorted repository-hosted copies first. In practice,
    publisher-hosted "best" links (Nature, PNAS, Wiley, ...) are frequently
    bot-blocked server-side (redirect-to-login, Cloudflare challenge, 403)
    even though they're legitimately open access, while institutional
    repository / preprint-server copies (HAL, eScholarship, university
    archives) almost always serve a plain PDF with no such wall. Trying
    every candidate in this order (see services/fulltext.py) is what
    actually gets a paper embeddable, not just correctly licensed.
    """
    settings = get_settings()
    try:
        resp = httpx.get(f"{_BASE_URL}/{doi}", params={"email": settings.unpaywall_email}, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            _logger.warning(
                "Unpaywall rejected UNPAYWALL_EMAIL=%r (422) — set a real email in .env, "
                "the placeholder is blocklisted. Full-text links will stay degraded until then.",
                settings.unpaywall_email,
            )
        return None
    except (httpx.HTTPError, ValueError):
        return None

    best_oa = data.get("best_oa_location") or {}
    locations = list(data.get("oa_locations") or [])
    if best_oa and best_oa not in locations:
        locations.insert(0, best_oa)

    candidates: list[str] = []
    seen: set[str] = set()
    for loc in sorted(locations, key=lambda l: l.get("host_type") != "repository"):
        url = loc.get("url_for_pdf") or loc.get("url")
        if url and url not in seen:
            seen.add(url)
            candidates.append(url)

    return {
        "is_oa": bool(data.get("is_oa")),
        "oa_url": candidates[0] if candidates else None,
        "oa_candidates": candidates,
    }
