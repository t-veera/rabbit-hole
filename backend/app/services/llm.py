"""Translates a plain-language interest into a real academic search query + field.

Uses the Anthropic API when ANTHROPIC_API_KEY is set. Without a key, falls
back to a naive heuristic so the app still runs end-to-end (just with a
dumber translation step) — see .env.example for how to add a real key.
"""

import json
import re

from app.config import get_settings
from app.field_routing import KNOWN_FIELDS

TRANSLATE_SYSTEM_PROMPT = f"""You translate a plain-language research interest into:
1. A real academic search query (the kind of terms a researcher would type into PubMed/arXiv/OpenAlex) — expand jargon, add synonyms, keep it concise.
2. The single best-matching field from this fixed list: {", ".join(KNOWN_FIELDS)}.

Respond with ONLY a JSON object: {{"translated_query": "...", "field": "..."}}"""

_STOPWORDS = {"the", "a", "an", "and", "of", "in", "on", "about", "for", "to"}


def _naive_translate(raw_query: str) -> tuple[str, str]:
    words = [w for w in re.findall(r"[a-zA-Z0-9\-]+", raw_query.lower()) if w not in _STOPWORDS]
    translated = " ".join(words) if words else raw_query
    field = "general_science"
    return translated, field


def translate_query(raw_query: str) -> tuple[str, str]:
    """Returns (translated_query, inferred_field)."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return _naive_translate(raw_query)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            system=TRANSLATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_query}],
        )
        text = message.content[0].text.strip()
        # Models sometimes wrap JSON in a fence despite instructions; strip it.
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        data = json.loads(text)
        translated = data.get("translated_query") or raw_query
        field = data.get("field") if data.get("field") in KNOWN_FIELDS else "general_science"
        return translated, field
    except Exception:
        # Any API/parsing failure degrades to the naive path rather than breaking search.
        return _naive_translate(raw_query)
