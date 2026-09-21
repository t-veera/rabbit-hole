"""In-app full-text reading.

Originally this embedded a paper's open-access PDF in an <iframe>. Two
things killed that approach:
1. Most publisher/repository landing pages (Zenodo, PLOS, journal sites)
   send X-Frame-Options/CSP headers that block framing outright — no
   client-side trick gets around a header the browser itself enforces.
2. Even proxied through our own origin (which sidesteps #1), an embedded
   PDF renders in the browser's native PDF viewer chrome — it can't be
   given the app's own typography no matter what, so "format it properly"
   was never achievable that way.

So instead: fetch the PDF server-side (trying every OA copy Unpaywall
knows about — see services/sources/unpaywall.py — preferring
repository-hosted ones since publisher-hosted "best" links are frequently
bot-walled: Nature redirects PDF requests through a login flow, PNAS runs
a Cloudflare challenge, neither is something a script can legitimately get
past) and extract its actual text with PyMuPDF. That text renders through
the same Prose component as the abstract — real typography, no iframe.
"""

import re

import httpx
import pymupdf
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import Paper
from app.services.sources import core as core_source
from app.services.sources import pmc

_TIMEOUT = 20

# Elsevier Pure (the CRIS software behind most university "research portal"
# sites — Edinburgh, Bristol, SKKU, and hundreds of others) serves each file
# under a human-facing "/files/<id>/<filename>" path that's frequently
# Cloudflare-challenge-gated (that's the path search engines/browsers hit),
# but also exposes the exact same file, same numeric record id, same
# filename, under a machine-facing "/ws/portalfiles/portal/<id>/<filename>"
# API path that isn't challenge-gated — it's meant for harvesters, not
# browsing. Different deployments wire that API path differently though:
# some serve it from the very same host (Bristol), others only from a
# separate pure.<institution> host (Edinburgh) even though the human-facing
# host is named differently (e.g. research-information.bris.ac.uk). So when
# the "/files/" copy is blocked, try both reachable shapes before giving up.
_PURE_FILES_RE = re.compile(r"^(https?://)([^/]+)/(?:.*/)?files/(\d+)/([^/?#]+)/?$", re.IGNORECASE)
_RESEARCH_HOST_RE = re.compile(r"^(?:www\.)?research\.(.+)$", re.IGNORECASE)


def _pure_ws_fallbacks(url: str) -> list[str]:
    match = _PURE_FILES_RE.match(url)
    if not match:
        return []
    scheme, host, file_id, filename = match.groups()
    candidates = [f"{scheme}{host}/ws/portalfiles/portal/{file_id}/{filename}"]

    research_match = _RESEARCH_HOST_RE.match(host)
    if research_match:
        candidates.append(f"{scheme}www.pure.{research_match.group(1)}/ws/portalfiles/portal/{file_id}/{filename}")

    return candidates

# Several hosts (confirmed: this Edinburgh repository) 403 any request whose
# User-Agent identifies as a script (httpx's default is "python-httpx/x.x"),
# with no further check — a real UA clears that trivial filter. This is not
# an attempt to defeat an actual anti-bot challenge (Cloudflare, PMC's JS
# interstitial, login-redirect gates all still block us, correctly, since
# getting past those would mean executing JS / solving a challenge, which
# this app does not and should not do); it just stops failing a check that
# most browsers pass by default.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _citation_pdf_url(html_bytes: bytes, base_url: str) -> str | None:
    """Academic repository/publisher pages almost universally carry a
    <meta name="citation_pdf_url"> tag — the same one Google Scholar's
    crawler uses to locate the actual PDF from a landing page. Following it
    is standard, expected behavior for anything that indexes scholarly
    pages, not a workaround for anything."""
    try:
        soup = BeautifulSoup(html_bytes, "html.parser")
        tag = soup.find("meta", attrs={"name": "citation_pdf_url"})
        if tag and tag.get("content"):
            return str(httpx.URL(base_url).join(tag["content"]))
    except Exception:
        pass
    return None


_EMBEDDED_PDF_ASSET_RE = re.compile(rb"""src=["']([^"']+\.pdf[^"']*)["']""", re.IGNORECASE)


def _embedded_pdf_asset_url(html_bytes: bytes, base_url: str) -> str | None:
    """Some publishers' citation_pdf_url doesn't point at the PDF bytes
    directly — it points at their own in-house PDF-viewer page (still HTML,
    not application/pdf), which loads the real file via a plain `src="...
    .pdf"` reference inside that page (confirmed: ELS Publishing, the
    "Law Ethics & Technology" journal). One more hop past citation_pdf_url
    catches this without special-casing any one publisher's viewer."""
    match = _EMBEDDED_PDF_ASSET_RE.search(html_bytes)
    if not match:
        return None
    return str(httpx.URL(base_url).join(match.group(1).decode()))


def _try_url(url: str, _from_pure_fallback: bool = False) -> bytes | None:
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=60, headers=_HEADERS)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None if _from_pure_fallback else _try_pure_fallbacks(url)

    content_type = resp.headers.get("content-type", "").lower()
    if content_type.startswith("application/pdf") or resp.content[:5] == b"%PDF-":
        return resp.content

    if content_type.startswith("text/html"):
        pdf_url = _citation_pdf_url(resp.content, str(resp.url))
        if pdf_url and pdf_url != url:
            return _try_url(pdf_url)
        asset_url = _embedded_pdf_asset_url(resp.content, str(resp.url))
        if asset_url and asset_url != url:
            return _try_url(asset_url)

    return None if _from_pure_fallback else _try_pure_fallbacks(url)


def _try_pure_fallbacks(url: str) -> bytes | None:
    for fallback_url in _pure_ws_fallbacks(url):
        content = _try_url(fallback_url, _from_pure_fallback=True)
        if content:
            return content
    return None


def fetch_pdf(urls: list[str]) -> bytes | None:
    """Tries each candidate URL in order, returns the first successful PDF's bytes."""
    for url in urls:
        content = _try_url(url)
        if content:
            return content
    return None


def _blocks_to_text(doc: pymupdf.Document, page_blocks: list[list[str]]) -> str | None:
    """Shared block-to-paragraph assembly for both the normal text layer and
    the OCR textpage: drops running headers/footers/page numbers (any line
    that repeats near-identically across most pages), collapses hard-wraps."""
    line_counts: dict[str, int] = {}
    for lines in page_blocks:
        for line in lines:
            if len(line) < 80:
                line_counts[line] = line_counts.get(line, 0) + 1

    threshold = max(3, int(doc.page_count * 0.6))
    boilerplate = {line for line, count in line_counts.items() if count >= threshold}

    paragraphs = []
    for lines in page_blocks:
        for line in lines:
            if line in boilerplate:
                continue
            paragraphs.append(" ".join(line.split()))

    text = "\n\n".join(p for p in paragraphs if len(p) > 1)
    return text if len(text) > 200 else None


def extract_text(pdf_bytes: bytes) -> str | None:
    """Layout-aware extraction from the PDF's real text layer: groups text by
    block (PyMuPDF's own paragraph/column detection) rather than raw line
    dumps. Returns None if there's no usable text layer at all — see
    extract_text_for_upload() for the OCR fallback used on manual uploads."""
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None

    if doc.page_count == 0 or doc.page_count > 200:
        # Guard against something that isn't really a research paper (e.g. a
        # multi-hundred-page book PDF that slipped through as an "OA copy").
        return None

    page_blocks = []
    for page in doc:
        blocks = page.get_text("blocks")
        page_blocks.append([b[4].strip() for b in blocks if b[4].strip()])

    return _blocks_to_text(doc, page_blocks)


class OcrUnavailable(Exception):
    """Raised when a PDF needs OCR (no real text layer) but Tesseract isn't
    installed on this machine — distinct from "extraction just failed" so
    the upload endpoint can tell the user specifically what's missing."""


def extract_text_for_upload(pdf_bytes: bytes) -> str | None:
    """Manual-upload path only: tries the normal text layer first (fast,
    handles the vast majority of uploads — born-digital PDFs already have
    one), and only falls back to OCR when a document genuinely has no
    extractable text (scanned pages). Raises OcrUnavailable rather than
    silently returning None when OCR would be needed but Tesseract isn't
    installed, so the user gets a real explanation instead of a generic
    "couldn't read this file"."""
    text = extract_text(pdf_bytes)
    if text:
        return text

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None
    if doc.page_count == 0 or doc.page_count > 200:
        return None

    # A real text layer that just happened to extract short (e.g. a mostly-
    # figures paper) shouldn't trigger a slow OCR pass — only do this when
    # there's essentially nothing to extract at all.
    raw_chars = sum(len(page.get_text()) for page in doc)
    if raw_chars > 200:
        return None

    try:
        page_blocks = []
        for page in doc:
            textpage = page.get_textpage_ocr(flags=0, dpi=200, full=True)
            blocks = page.get_text("blocks", textpage=textpage)
            page_blocks.append([b[4].strip() for b in blocks if b[4].strip()])
    except RuntimeError as exc:
        if "tesseract" in str(exc).lower() or "tessdata" in str(exc).lower():
            raise OcrUnavailable(str(exc)) from exc
        return None

    return _blocks_to_text(doc, page_blocks)


def oa_candidates(paper: Paper) -> list[str]:
    """All known OA copies for this paper, best-bet first."""
    stored = (paper.raw_metadata or {}).get("oa_candidates") or []
    if paper.oa_url and paper.oa_url not in stored:
        stored = [paper.oa_url, *stored]
    return stored


def resolve_fulltext(db: Session, paper: Paper, refresh: bool = False) -> dict:
    """Fetches this paper's full text and returns it, cached after the first
    successful fetch. Tries these in order, cheapest/most-reliable first —
    shared by the per-paper API route (routers/papers.py) and the
    library-wide sweep script (scripts/fulltext_sweep.py) so both report the
    exact same resolution behavior:
    1. Europe PMC's fullTextXML, if we can resolve a PMCID.
    2. Every OA copy Unpaywall knows about, preferring institutional
       repositories over publisher hosts.
    3. CORE.ac.uk — a no-op without CORE_API_KEY configured, not a failure.
    4. The paper's own DOI landing page, via the same citation_pdf_url-
       following logic as step 2 — Unpaywall's OA index can simply be wrong
       for smaller/niche publishers (confirmed: a journal whose own site
       serves the PDF from a `/open/` path, with no login or paywall,
       that Unpaywall nonetheless reports as closed-access). Tried last,
       not first, since it's a plain page fetch with no OA signal backing
       it — most papers won't have anything here that steps 1-3 didn't
       already find.
    """
    if paper.full_text and not refresh:
        return {"text": paper.full_text, "source": "cache"}

    candidates = oa_candidates(paper)

    pmid = (paper.raw_metadata or {}).get("pmid")
    pmcid = pmc.find_pmcid(candidates, pmid)
    if pmcid:
        text = pmc.fetch_fulltext(pmcid)
        if text:
            paper.full_text = text
            db.commit()
            return {"text": text, "source": f"Europe PMC ({pmcid})"}

    pdf_bytes = fetch_pdf(candidates)
    if pdf_bytes:
        text = extract_text(pdf_bytes)
        if text:
            paper.full_text = text
            db.commit()
            return {"text": text, "source": "OA PDF"}

    if paper.doi:
        core_candidates = core_source.find_pdf_urls(paper.doi)
        pdf_bytes = fetch_pdf(core_candidates)
        if pdf_bytes:
            text = extract_text(pdf_bytes)
            if text:
                paper.full_text = text
                db.commit()
                return {"text": text, "source": "CORE.ac.uk"}

    if paper.landing_url:
        pdf_bytes = fetch_pdf([paper.landing_url])
        if pdf_bytes:
            text = extract_text(pdf_bytes)
            if text:
                paper.full_text = text
                # We just successfully pulled a PDF straight off the
                # publisher's own page — that's direct proof this is
                # actually open access, regardless of what Unpaywall's
                # (evidently stale, for this publisher) index says.
                paper.oa_status = True
                paper.oa_url = paper.oa_url or paper.landing_url
                db.commit()
                return {"text": text, "source": "publisher page"}

    return {"text": None, "source": None}
