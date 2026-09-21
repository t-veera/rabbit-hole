"""PubMed via NCBI E-utilities — no key required (optional key raises rate limit).

https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

from datetime import datetime
from xml.etree import ElementTree

import httpx

from app.config import get_settings
from app.services.sources.base import NormalizedPaper

_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _api_key_params() -> dict:
    settings = get_settings()
    return {"api_key": settings.ncbi_api_key} if settings.ncbi_api_key else {}


def search(query: str, max_results: int = 20) -> list[NormalizedPaper]:
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "relevance",
        "retmode": "json",
        **_api_key_params(),
    }
    try:
        resp = httpx.get(f"{_BASE_URL}/esearch.fcgi", params=search_params, timeout=15)
        resp.raise_for_status()
        pmids = resp.json().get("esearchresult", {}).get("idlist", [])
    except (httpx.HTTPError, ValueError):
        return []

    if not pmids:
        return []

    fetch_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", **_api_key_params()}
    try:
        resp = httpx.get(f"{_BASE_URL}/efetch.fcgi", params=fetch_params, timeout=20)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    root = ElementTree.fromstring(resp.text)
    results: list[NormalizedPaper] = []
    for article in root.findall(".//PubmedArticle"):
        medline = article.find("MedlineCitation")
        if medline is None:
            continue
        art = medline.find("Article")
        if art is None:
            continue

        title = (art.findtext("ArticleTitle") or "").strip()
        abstract_parts = [t.text or "" for t in art.findall("Abstract/AbstractText")]
        abstract = " ".join(abstract_parts).strip() or None

        pmid = medline.findtext("PMID") or ""
        doi = None
        for eid in article.findall("PubmedData/ArticleIdList/ArticleId"):
            if eid.get("IdType") == "doi":
                doi = eid.text

        journal = art.findtext("Journal/Title")

        pub_date_el = art.find("Journal/JournalIssue/PubDate")
        published_date = None
        if pub_date_el is not None:
            year = pub_date_el.findtext("Year")
            month = pub_date_el.findtext("Month") or "Jan"
            day = pub_date_el.findtext("Day") or "1"
            if year:
                try:
                    published_date = datetime.strptime(f"{year} {month} {day}", "%Y %b %d")
                except ValueError:
                    try:
                        published_date = datetime.strptime(year, "%Y")
                    except ValueError:
                        pass

        authors = []
        corresponding_email = None
        for author_el in art.findall("AuthorList/Author"):
            last = author_el.findtext("LastName") or ""
            fore = author_el.findtext("ForeName") or ""
            name = f"{fore} {last}".strip()
            if not name:
                continue
            affiliation = author_el.findtext("AffiliationInfo/Affiliation")
            email = None
            if affiliation and "@" in affiliation:
                email = next((tok.strip(".,;()") for tok in affiliation.split() if "@" in tok), None)
                if email and not corresponding_email:
                    corresponding_email = email
            authors.append({"name": name, "affiliation": affiliation, "email": email})

        results.append(
            NormalizedPaper(
                title=title,
                abstract=abstract,
                doi=doi,
                external_id=f"pmid:{pmid}",
                venue=journal,
                published_date=published_date,
                landing_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                oa_url=None,
                oa_status=False,
                openalex_id=None,
                authors=authors,
                raw_metadata={"source": "pubmed", "pmid": pmid, "corresponding_email": corresponding_email},
            )
        )
    return results
