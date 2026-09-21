"""Citation export (BibTeX/RIS) and notes export (markdown/plain text)."""

import re

from app.models import Note, Paper


def _bibtex_key(paper: Paper) -> str:
    first_author = paper.authors[0].researcher.name.split()[-1] if paper.authors else "unknown"
    year = paper.published_date.year if paper.published_date else "nd"
    slug = re.sub(r"[^a-zA-Z0-9]", "", first_author)
    return f"{slug}{year}"


def to_bibtex(paper: Paper) -> str:
    authors = " and ".join(a.researcher.name for a in sorted(paper.authors, key=lambda a: a.author_order))
    year = paper.published_date.year if paper.published_date else ""
    entry_type = "article"
    fields = {
        "author": authors,
        "title": paper.title,
        "year": str(year),
        "journal": paper.venue or "",
        "doi": paper.doi or "",
        "url": paper.landing_url or "",
    }
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if v)
    return f"@{entry_type}{{{_bibtex_key(paper)},\n{body}\n}}"


def to_ris(paper: Paper) -> str:
    lines = ["TY  - JOUR"]
    for author in sorted(paper.authors, key=lambda a: a.author_order):
        lines.append(f"AU  - {author.researcher.name}")
    lines.append(f"TI  - {paper.title}")
    if paper.venue:
        lines.append(f"JO  - {paper.venue}")
    if paper.published_date:
        lines.append(f"PY  - {paper.published_date.year}")
    if paper.doi:
        lines.append(f"DO  - {paper.doi}")
    if paper.landing_url:
        lines.append(f"UR  - {paper.landing_url}")
    if paper.abstract:
        lines.append(f"AB  - {paper.abstract}")
    lines.append("ER  - ")
    return "\n".join(lines)


def _note_title(note: Note, item_titles: dict) -> str:
    if note.item_id is None:
        return "Freeform note"
    return item_titles.get((note.item_type, note.item_id), "(untitled)")


def notes_to_markdown(notes: list[Note], item_titles: dict) -> str:
    out = ["# Exported Notes\n"]
    for note in notes:
        title = _note_title(note, item_titles)
        out.append(f"## {title}")
        if note.topic_tag:
            out.append(f"*Tag: {note.topic_tag}*")
        out.append(f"*{note.created_at.isoformat()}*\n")
        if note.quote_text:
            out.append(f"> {note.quote_text}\n")
        out.append(note.note_text)
        out.append("\n---\n")
    return "\n".join(out)


def notes_to_plain_text(notes: list[Note], item_titles: dict) -> str:
    out = []
    for note in notes:
        title = _note_title(note, item_titles)
        out.append(f"{title} ({note.created_at.isoformat()})")
        if note.topic_tag:
            out.append(f"Tag: {note.topic_tag}")
        if note.quote_text:
            out.append(f'Quote: "{note.quote_text}"')
        out.append(note.note_text)
        out.append("-" * 40)
    return "\n".join(out)
