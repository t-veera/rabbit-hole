"""Best-effort researcher profile enrichment: ORCID first, faculty-page scrape second.

ORCID's public API exposes verified education/employment history for
researchers who've filled it in, which we use for "degree" and
"affiliation". It does not host a photo. A university faculty-page photo
scrape needs a web search step (Claude Code has no bundled search API key
by default) — this is a documented gap, not a fabrication: we leave photo
blank and fall back to an initials avatar in the UI rather than guess.
"""

import httpx
from bs4 import BeautifulSoup

_ORCID_BASE = "https://pub.orcid.org/v3.0"
_HEADERS = {"Accept": "application/json"}


def enrich_from_orcid(orcid: str) -> dict:
    """Returns {"degree": str|None, "affiliation": str|None, "photo_url": None}."""
    out = {"degree": None, "affiliation": None, "photo_url": None}
    try:
        resp = httpx.get(f"{_ORCID_BASE}/{orcid}/educations", headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return out

    groups = data.get("affiliation-group", [])
    if groups:
        summary = groups[0]["summaries"][0]["education-summary"]
        role = summary.get("role-title")
        org = (summary.get("organization") or {}).get("name")
        if role:
            out["degree"] = role
        if org:
            out["affiliation"] = org
    return out


def scrape_faculty_bio(faculty_page_url: str) -> dict:
    """Lightweight best-effort scrape of a known faculty bio page URL.

    Only runs when a URL is already known (e.g. from OpenAlex/ORCID linked
    data) — this app does not perform open-web search to locate one.
    """
    out = {"degree": None, "photo_url": None}
    try:
        resp = httpx.get(faculty_page_url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return out

    soup = BeautifulSoup(resp.text, "html.parser")

    img = soup.find("img", class_=lambda c: c and "headshot" in c.lower()) or soup.find(
        "img", alt=lambda a: a and "photo" in a.lower()
    )
    if img and img.get("src"):
        out["photo_url"] = str(httpx.URL(faculty_page_url).join(img["src"]))

    text = soup.get_text(" ", strip=True)
    for degree in ("Ph.D.", "PhD", "M.D.", "MD", "D.Phil.", "Sc.D."):
        if degree in text:
            out["degree"] = degree
            break

    return out
