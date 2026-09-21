"""Maps an inferred field to the academic APIs that should be queried for it.

The LLM translation step (services/llm.py) returns one of these field keys;
the aggregator (services/aggregator.py) uses this table to decide which
source modules to call.
"""

FIELD_SOURCE_MAP: dict[str, list[str]] = {
    "biology": ["pubmed", "biorxiv", "medrxiv", "openalex"],
    "medicine": ["pubmed", "medrxiv", "openalex"],
    "genomics": ["pubmed", "biorxiv", "openalex"],
    "physics": ["arxiv", "openalex"],
    "astronomy": ["arxiv", "openalex"],
    "computer_science": ["arxiv", "openalex"],
    "math": ["arxiv", "openalex"],
    "economics": ["openalex"],  # RePEc/SSRN have no stable free JSON API; OpenAlex covers econ well
    "anthropology": ["openalex", "pubmed"],  # ancient-DNA/paleoanthropology studies are PubMed-indexed too
    "humanities": ["openalex"],
    "politics": ["openalex"],
    # Broader than the others on purpose: this is also what every query gets
    # routed to when there's no ANTHROPIC_API_KEY configured (the naive
    # fallback in services/llm.py always guesses "general_science", since it
    # has no real classification ability) — OpenAlex alone under-covers
    # biology/anthropology-adjacent topics in that fallback path.
    "general_science": ["openalex", "pubmed"],
}

DEFAULT_FIELD = "general_science"

KNOWN_FIELDS = list(FIELD_SOURCE_MAP.keys())


def sources_for_field(field: str | None) -> list[str]:
    return FIELD_SOURCE_MAP.get(field or DEFAULT_FIELD, FIELD_SOURCE_MAP[DEFAULT_FIELD])
