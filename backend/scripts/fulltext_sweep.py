"""Sweeps every saved paper and reports how many now resolve to full text
vs. stay blurb-only, broken down by which source resolved it.

Reuses the exact same resolution chain as the per-paper "read in app" button
(services/fulltext.py:resolve_fulltext) — Europe PMC -> Unpaywall OA copies
-> CORE.ac.uk — so this reports real, current-code resolution rates, not a
separate/optimistic estimate. Already-resolved papers hit the cache path
(no network calls); only papers without full_text yet trigger a real fetch
attempt, so re-running this after a code change to the fetch chain is cheap
for papers already solved and only "spends" time on the genuinely unresolved
ones.

Usage:
    .venv/bin/python scripts/fulltext_sweep.py [--limit N]
"""

import argparse
import sys
import time
from collections import Counter

from app.db import SessionLocal
from app.models import Paper
from app.services.fulltext import resolve_fulltext


def _source_bucket(source: str | None) -> str:
    if source is None:
        return "none"
    if source.startswith("Europe PMC"):
        return "Europe PMC"
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Only sweep the first N papers (for a quick check).")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Paper).order_by(Paper.created_at)
        if args.limit:
            query = query.limit(args.limit)
        papers = query.all()

        total = len(papers)
        buckets: Counter[str] = Counter()
        errors: list[tuple[str, str]] = []

        print(f"Sweeping {total} papers...\n")
        started = time.monotonic()

        for i, paper in enumerate(papers, 1):
            try:
                result = resolve_fulltext(db, paper, refresh=False)
                buckets[_source_bucket(result["source"])] += 1
            except Exception as exc:  # a single bad paper (network blip, malformed PDF) shouldn't kill the sweep
                buckets["error"] += 1
                errors.append((str(paper.id), str(exc)))

            if i % 20 == 0 or i == total:
                elapsed = time.monotonic() - started
                print(f"  {i}/{total} ({elapsed:.0f}s elapsed)", file=sys.stderr)

        resolved = total - buckets["none"] - buckets["error"]

        print("\n--- Full-text resolution sweep ---")
        print(f"Total papers:     {total}")
        print(f"Resolved:         {resolved} ({resolved / total * 100:.1f}%)" if total else "Resolved:         0")
        print(f"Blurb-only:       {buckets['none']}")
        if buckets["error"]:
            print(f"Errors:           {buckets['error']}")
        print("\nBy source:")
        for source, count in sorted(buckets.items(), key=lambda kv: -kv[1]):
            if source in ("none", "error"):
                continue
            print(f"  {source:<20} {count}")

        if errors:
            print(f"\n{len(errors)} paper(s) raised an error during resolution (not counted as blurb-only):")
            for paper_id, message in errors[:10]:
                print(f"  {paper_id}: {message}")
            if len(errors) > 10:
                print(f"  ...and {len(errors) - 10} more")
    finally:
        db.close()


if __name__ == "__main__":
    main()
