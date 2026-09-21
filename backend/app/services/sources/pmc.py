"""PubMed Central full text — via Europe PMC, not NCBI's own OA service.

NCBI's legacy PMC OA Web Service (www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi)
is dead — confirmed by direct request, returns a 404 diagnostic page, not a
redirect. NCBI decommissioned it as part of migrating PMC to
pmc.ncbi.nlm.nih.gov, the same migration that added the "Preparing to
download..." JS interstitial blocking direct PDF fetches (see
services/fulltext.py).

Europe PMC's fullTextXML endpoint is the real fix: it mirrors PMC's open
content, has no bot wall, and returns real JATS XML — genuine paragraph
structure, better than extracting text from a PDF.
"""

import re
from xml.etree import ElementTree

import httpx

_EUROPEPMC_FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
_ID_CONVERTER_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"

_PMCID_RE = re.compile(r"PMC\d+")
# Some sources (confirmed: Unpaywall) give a PMC article URL with the
# numeric id but no "PMC" prefix (ncbi.nlm.nih.gov/pmc/articles/5385025
# rather than .../articles/PMC5385025) — still a valid PMC article, just
# missed by _PMCID_RE, which sends this straight to the (often bot-walled)
# PDF path instead of the reliable Europe PMC XML fetch below.
_BARE_PMC_URL_RE = re.compile(r"ncbi\.nlm\.nih\.gov/pmc/articles/(\d+)", re.IGNORECASE)


def find_pmcid(candidate_urls: list[str], pmid: str | None) -> str | None:
    """Looks for a PMCID in known OA URLs first (free), falls back to NCBI's
    ID Converter if we only have a PMID (e.g. from a PubMed-sourced record)."""
    for url in candidate_urls:
        match = _PMCID_RE.search(url)
        if match:
            return match.group(0)
    for url in candidate_urls:
        match = _BARE_PMC_URL_RE.search(url)
        if match:
            return f"PMC{match.group(1)}"

    if not pmid:
        return None
    try:
        resp = httpx.get(_ID_CONVERTER_URL, params={"ids": pmid, "format": "json"}, timeout=15)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if records and records[0].get("pmcid"):
            return records[0]["pmcid"]
    except (httpx.HTTPError, ValueError):
        pass
    return None


def fetch_fulltext(pmcid: str) -> str | None:
    """Returns clean paragraph text extracted from Europe PMC's JATS XML, or
    None if this record isn't in Europe PMC's open subset."""
    try:
        resp = httpx.get(_EUROPEPMC_FULLTEXT_URL.format(pmcid=pmcid), timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    try:
        root = ElementTree.fromstring(resp.content)
    except ElementTree.ParseError:
        return None

    body = root.find(".//body")
    if body is None:
        return None

    def _text(el) -> str:
        return " ".join("".join(el.itertext()).split())

    paragraphs = []
    for el in body.iter():
        if el.tag in ("title", "p"):
            text = _text(el)
            if text:
                paragraphs.append(text)

    text = "\n\n".join(paragraphs)
    return text if len(text) > 200 else None
