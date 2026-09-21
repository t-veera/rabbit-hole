# Rabbit Hole

Self-hosted research discovery app. Enter a plain-language interest, it gets
translated into real academic search terms, pulls matching papers + science
journalism from multiple sources, surfaces researcher profiles, and presents
it all in an editorial, RSS-reader-style UI with a citation/manual graph view
and note-taking.

Phase 1 (this build): local-only, single-user, Postgres (containerized DB,
app runs locally). Phase 2 (later): Dockerize the app itself for Synology —
no DB migration needed, since Postgres already runs in Docker.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic, Postgres
- Frontend: React + Vite, plain CSS design system (no Tailwind/shadcn look)
- Background jobs: APScheduler (in-process, per-topic refresh cadence)
- Sources: arXiv, PubMed, bioRxiv/medRxiv, OpenAlex, Unpaywall, Open Library, user RSS feeds
- Graph: react-force-graph-2d
- Fonts: Fraunces (display), Literata (reading text), Work Sans (UI) — light/dark theme, toggle in the sidebar

## Ports used

Picked non-default ports because this machine already has other projects on
5432/8000:

| Service | Port |
|---|---|
| Postgres (docker) | 5433 |
| Backend (FastAPI) | 8420 |
| Frontend (Vite) | 5173 |

## First-time setup

```bash
# 1. Start Postgres
docker-compose up -d

# 2. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example .env   # edit ANTHROPIC_API_KEY, UNPAYWALL_EMAIL, OPENALEX_MAILTO
.venv/bin/python -m alembic upgrade head

# 3. Frontend
cd ../frontend
npm install
cp .env.example .env
```

## Running

```bash
# Terminal 1
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8420

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173.

## API keys (`backend/.env`)

Only one is a real secret — the rest are free/no-signup, required only by
usage terms or for higher rate limits:

| Var | Needed for | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM keyword translation | Real key needed for good translation. Without it, translation falls back to a naive passthrough — app still runs, just dumber search terms. |
| `DATABASE_URL` | Postgres connection | Pre-filled to match `docker-compose.yml`. |
| `UNPAYWALL_EMAIL` | Open-access lookup | Just an email, no signup — but **must be real**: Unpaywall hard-rejects the placeholder `you@example.com` (422 error) and every OA lookup silently fails until you swap it in, degrading full-text links to weaker fallbacks. |
| `OPENALEX_MAILTO` | Faster OpenAlex responses | Just an email, no signup — gets the "polite pool". |
| `NCBI_API_KEY` | PubMed | Optional — raises rate limit 3→10 req/s. |
| `SEMANTIC_SCHOLAR_API_KEY` | (unused currently) | Optional, reserved for future use. |

arXiv, OpenAlex, bioRxiv/medRxiv, Unpaywall, PubMed, and RSS all work with
zero signup.

## What's implemented

All 17 Phase 1 features from the spec, plus the graph view:

- Plain-language keyword input, LLM-translated (editable before running)
- Field/topic filters
- Custom sources (searched first, tagged "from your sources" vs "discovered")
- Chronological card-based feed with OA badges
- Paper detail view (abstract, in-app full-text PDF reader when embeddable, citation export, clickable authors)
- Books (via Open Library — free, no key) alongside papers and journalism in search + library results
- Researcher profiles (ORCID + OpenAlex enrichment, initials-avatar fallback)
- Journalism track (Aeon, Quanta, Nature News, Science News curated by default)
- Bookmarks/lists (many-to-many, papers + articles)
- New-item notifications per topic since last visit
- Highlight & annotate (select text on any paper/article abstract)
- Notes export (Markdown/plain text, filterable by topic tag + date range)
- Reading status (unread/read/skimmed) + reading queue vs reference library
- Side-by-side split-pane reading (`/split?a=paper:<id>&b=article:<id>`)
- Full-text library search across papers, articles, and notes
- BibTeX/RIS citation export (single paper or whole list)
- Digest cadence per topic (real-time ~15min / daily / weekly), backed by APScheduler
- Graph view: linked vs saved nodes (combined visual state for both), manual
  vs citation edges (dashed), citation-layer toggle, orphan filter

## Known limitations (by design, not bugs)

- **Faculty-page photo scraping** only runs when a URL is already known from
  linked data — the app does not perform open-web search to *locate* a
  faculty page, since that needs a search API key not listed in the spec.
  Photo/degree fall back to ORCID education records, then an initials avatar.
- **bioRxiv/medRxiv search** — their public API has no free-text search
  endpoint, only a date-range listing. We fetch a 30-day window and filter
  client-side by keyword match.
- **RePEc/SSRN** (economics) have no stable free JSON API, so economics
  routes through OpenAlex only, per the spec's "where API/RSS available" caveat.
- **"Real-time" cadence** means a 15-minute poll, not push — none of the
  upstream APIs offer a push/webhook mechanism.
- **In-app PDF reading only works for direct, unblocked PDFs.** We proxy the
  PDF through our own backend (bypassing X-Frame-Options, which is what
  actually breaks a plain `<iframe src>` for most sources) and check
  embeddability first — but some publishers (confirmed: Wiley) return a
  403 to any non-browser request regardless of headers, which is bot
  detection on their end, not something a client can legitimately work
  around. When that happens the app shows the abstract plus an honest "open
  in new tab" link rather than faking an embed. arXiv/bioRxiv/medRxiv PDFs
  and most repository-hosted OA copies embed fine.
- **Without a real `ANTHROPIC_API_KEY`**, every query gets field-classified
  as `general_science` (routed to OpenAlex + PubMed) since the naive
  fallback can't actually classify anything — a real key unlocks accurate
  per-query field routing (e.g. "anthropology" → OpenAlex + PubMed
  specifically, rather than the broad default) and much better book-search
  terms (Open Library search wants concise topical terms, not a full
  natural-language sentence).

## Project layout

```
backend/app/
  models.py, schemas.py      — Postgres schema (SQLAlchemy) / API types (Pydantic)
  routers/                   — one file per feature area
  services/
    llm.py                   — Anthropic keyword translation
    aggregator.py            — search orchestration (your sources first, then broad APIs)
    sources/                 — arxiv, pubmed, biorxiv, openalex, unpaywall, rss
    citation.py               — OpenAlex-derived citation graph edges
    export.py                 — BibTeX/RIS/Markdown export
    scheduler.py               — APScheduler per-topic refresh jobs
    researcher_enrichment.py  — ORCID + faculty-page scrape
  field_routing.py            — field → source-module mapping
frontend/src/
  pages/                      — one per route
  components/                 — ItemCard, ItemReader, Highlighter, Graph pieces, etc.
docker-compose.yml             — Postgres only (Phase 1); app runs locally
backend/Dockerfile              — ready for Phase 2, not part of the local dev flow yet
```

Structured for Phase 2: all config is env-based, no localhost-hardcoded
assumptions, no OS-specific paths — Dockerizing the app later just means
adding a service block pointing at `backend/Dockerfile`, no DB migration.

`backend/Dockerfile` exists early because of one specific dependency: OCR
(manual PDF upload's fallback for scanned pages) needs the `tesseract-ocr`
system package, which a local dev machine may not have installed. The
Dockerfile bakes it in and has been built + tested (confirmed: OCR
correctly extracts text from an image-only PDF inside the container).
Build/run it standalone any time with:

```bash
docker build -t rabbit-hole-backend backend/
docker run --rm -p 8420:8420 --env-file backend/.env rabbit-hole-backend
```

(`DATABASE_URL` in that `.env` needs to be reachable from inside the
container — `localhost` won't resolve to the host machine's Postgres; use
`host.docker.internal` or run on the same Docker network as the `db`
service in `docker-compose.yml`.)
