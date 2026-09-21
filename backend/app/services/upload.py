"""Manual PDF upload: extract what we can from the file itself (title,
authors, DOI) so the confirm form starts pre-filled — user fixes whatever
the heuristics miss rather than typing everything from scratch. Reuses the
same extract_text() pipeline as fetched papers (services/fulltext.py), so
uploaded content gets identical formatting, no separate rendering path.
"""

import re

import pymupdf

_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>()]+", re.IGNORECASE)
_NAME_TOKEN_RE = re.compile(r"^[A-Z][a-zA-Z.\-']+(?:\s+[A-Z][a-zA-Z.\-']*\.?){1,3}$")
_WATERMARK_RE = re.compile(r"^arxiv[:\s]|^\s*©|preprint|submitted to", re.IGNORECASE)


def extract_doi(first_page_text: str) -> str | None:
    """Only searches page 1: a paper's *own* DOI (if it has one) is virtually
    always there near the header — searching the whole document would as
    often as not return a citation's DOI from the reference list instead,
    which is worse than no suggestion at all (silently wrong, not just
    missing)."""
    match = _DOI_RE.search(first_page_text)
    if not match:
        return None
    return match.group(0).rstrip(".,;")


def _first_page_title_and_author_zone(doc: pymupdf.Document) -> tuple[str | None, str]:
    """Largest-font line(s) on page 1 = title; the text directly beneath it
    (down to whatever mentions "abstract") is where author names usually sit."""
    if doc.page_count == 0:
        return None, ""

    page = doc[0]
    page_dict = page.get_text("dict")
    spans = []
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            # Rotated text (e.g. arXiv's vertical sidebar watermark, "arXiv:2301.00001v1 [cs.HC] ...")
            # is often the single largest font on the page — exclude anything not
            # roughly horizontal so it can't outrank the real title.
            dx, dy = line.get("dir", (1, 0))
            if abs(dy) > abs(dx):
                continue
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text and not _WATERMARK_RE.search(text):
                    spans.append({"text": text, "size": span.get("size", 0), "y": line.get("bbox", [0, 0, 0, 0])[1]})

    if not spans:
        return None, ""

    max_size = max(s["size"] for s in spans)
    title_spans = [s for s in spans if s["size"] >= max_size - 0.5]
    title = " ".join(s["text"] for s in title_spans).strip() or None
    if title and not (10 <= len(title) <= 300):
        title = None

    title_y = max((s["y"] for s in title_spans), default=0)
    zone_lines = [s["text"] for s in spans if title_y < s["y"] < title_y + 220]
    zone_text = " ".join(zone_lines)
    abstract_idx = zone_text.lower().find("abstract")
    if abstract_idx != -1:
        zone_text = zone_text[:abstract_idx]

    return title, zone_text


def _guess_authors(author_zone_text: str) -> list[str]:
    # Strip common affiliation/footnote markers (superscript numbers, *, †, ‡).
    cleaned = re.sub(r"[\d*†‡§¶,]+(?=\s|$)", " ", author_zone_text)
    tokens = re.split(r",|\band\b|;|\n", cleaned)
    names = []
    for token in tokens:
        token = token.strip()
        if _NAME_TOKEN_RE.match(token) and token not in names:
            names.append(token)
        if len(names) >= 12:
            break
    return names


def extract_draft(pdf_bytes: bytes) -> dict:
    """Returns {"suggested_title", "suggested_authors", "suggested_doi", "page_count"} —
    best effort only; the confirm step lets the user correct anything wrong/missing."""
    title = None
    authors: list[str] = []
    doi = None
    page_count = 0
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        page_count = doc.page_count
        meta_title = (doc.metadata or {}).get("title", "").strip()
        heuristic_title, author_zone = _first_page_title_and_author_zone(doc)
        # PDF metadata titles are often garbage ("Microsoft Word - draft2.docx");
        # prefer the largest-font-on-page-1 heuristic when metadata looks like that.
        title = heuristic_title or (meta_title if 10 <= len(meta_title) <= 300 else None)
        authors = _guess_authors(author_zone)
        if doc.page_count:
            doi = extract_doi(doc[0].get_text())
    except Exception:
        pass

    return {
        "suggested_title": title,
        "suggested_authors": authors,
        "suggested_doi": doi,
        "page_count": page_count,
    }
