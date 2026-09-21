"""Shared normalized-record shape every source module returns.

The aggregator (services/aggregator.py) consumes these dicts directly when
upserting Paper/Article rows, so every source module normalizes to this
shape regardless of the wire format its upstream API uses (XML, JSON, RSS).
"""

from datetime import datetime
from typing import TypedDict


class NormalizedAuthor(TypedDict, total=False):
    name: str
    orcid: str | None
    affiliation: str | None
    is_corresponding: bool
    email: str | None


class NormalizedPaper(TypedDict, total=False):
    title: str
    abstract: str | None
    doi: str | None
    external_id: str | None
    venue: str | None
    published_date: datetime | None
    landing_url: str | None
    oa_url: str | None
    oa_status: bool
    openalex_id: str | None
    authors: list[NormalizedAuthor]
    raw_metadata: dict
