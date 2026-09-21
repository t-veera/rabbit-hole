<div align="center">

# 🐇 Rabbit Hole

**A self-hosted research discovery app that turns a plain-language interest into a real academic search — then gives you an editorial, RSS-reader-style feed to read it in.**

[![CI](https://github.com/t-veera/rabbit-hole/actions/workflows/ci.yml/badge.svg)](https://github.com/t-veera/rabbit-hole/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB)](https://react.dev/)
[![Vibe Coded](https://img.shields.io/badge/built%20with-vibe%20coding%20%E2%9C%A8-ff69b4)](#-a-note-on-how-this-was-built)

</div>

---

## Introduction

You type something like *"how gut bacteria affect mood"* — no field names, no
boolean operators, no knowing which database to search. Rabbit Hole
translates that into real academic search terms, pulls matching papers and
science journalism from arXiv, PubMed, bioRxiv/medRxiv, OpenAlex, and your
own added sources, resolves open-access full text where it exists, and drops
it all into a chronological, editorial-style feed — with highlighting,
notes, reading lists, a citation graph, and per-topic digest scheduling.

It's Phase 1 of a two-phase build: local-only and single-user today
(Postgres in Docker, app running on your machine), with Phase 2 aimed at
Dockerizing the app itself for always-on self-hosting (e.g. a Synology box),
with no database migration required to get there.

#### 📝 A note on how this was built

This project is **vibe-coded** — designed and built through direct,
conversational collaboration with Claude (Anthropic's AI) rather than
written by hand line-by-line. Product decisions, review, and testing were
human-directed throughout; a large share of the implementation, debugging,
and this README were AI-assisted. Said plainly, up front, rather than left
for someone to discover in the commit history.

## Table of Contents

<details>
<summary>Click to expand</summary>

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running](#running)
- [Configuration](#configuration)
- [Known Limitations](#known-limitations-by-design-not-bugs)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

</details>

## Features

**Discovery & search**
- Plain-language input, LLM-translated into real academic search terms (editable before running)
- Field/topic filters, with your own custom sources searched first and tagged separately from discovered results
- Books (via Open Library) and curated science journalism (Aeon, Quanta, Nature News, Science News) alongside papers

**Reading experience**
- Chronological, card-based feed with open-access badges
- In-app full-text PDF reader (proxied + extracted server-side, not a raw iframe embed) when a publisher allows it
- Highlight & annotate any abstract or full text, side-by-side split-pane reading
- Reading status (unread / read / skimmed), separate reading queue vs. reference library

**Organization**
- Bookmarks and lists (many-to-many, across papers/articles/books/notes)
- Full-text library search across everything you've saved
- Notes export to Markdown/plain text, filterable by tag and date range
- BibTeX/RIS citation export, single item or whole list

**Researchers & connections**
- Researcher profiles enriched from ORCID + OpenAlex, with a "follow a person" mode that ingests their whole body of work
- Manual + citation graph view: linked vs. saved nodes, dashed citation edges, orphan filter

**Automation**
- Per-topic digest cadence (real-time / daily / weekly) via an in-process scheduler
- New-item notifications since your last visit, per topic

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + [SQLAlchemy](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/), [PostgreSQL](https://www.postgresql.org/) |
| Frontend | [React](https://react.dev/) + [Vite](https://vitejs.dev/), hand-rolled CSS design system (no Tailwind/shadcn look) |
| Background jobs | [APScheduler](https://apscheduler.readthedocs.io/), in-process, per-topic refresh cadence |
| Graph | [react-force-graph-2d](https://github.com/vasturiano/react-force-graph) |
| Sources | arXiv, PubMed, bioRxiv/medRxiv, OpenAlex, Unpaywall, Open Library, user RSS feeds |
| Typography | Fraunces (display), Literata (reading text), Work Sans (UI) — light/dark theme |

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/)
- Python 3.11+
- Node 20+

### Installation

**macOS / Linux**
```bash
./setup.sh
```

**Windows (PowerShell)**
```powershell
.\setup.ps1
```

Either script starts Postgres, creates the backend virtualenv, installs
dependencies, runs migrations, and installs frontend packages, in one shot.

<details>
<summary>Manual setup instead (any OS)</summary>

```bash
# 1. Start Postgres
docker compose up -d          # or: docker-compose up -d

# 2. Backend
cd backend
python3 -m venv .venv          # Windows: python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip.exe install -r requirements.txt
cp ../.env.example .env        # Windows: copy ..\.env.example .env
.venv/bin/python -m alembic upgrade head        # Windows: .venv\Scripts\alembic.exe upgrade head

# 3. Frontend
cd ../frontend
npm install
cp .env.example .env           # Windows: copy .env.example .env
```
</details>

API keys can be left blank in `.env` and added later from the app's
**Settings** page instead — see [Configuration](#configuration).

### Running

```bash
# Terminal 1
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8420
# Windows: .venv\Scripts\uvicorn.exe app.main:app --reload --port 8420

# Terminal 2
cd frontend && npm run dev
```

Open **http://localhost:5173**.

| Service | Port |
|---|---|
| Postgres (docker) | 5433 |
| Backend (FastAPI) | 8420 |
| Frontend (Vite) | 5173 |

*(Non-default ports, picked to avoid colliding with other local projects on 5432/8000.)*

## Configuration

Easiest path: leave `backend/.env` blank and add these from the app's
**Settings** page instead — they save to the database and take effect
immediately, no restart needed. `.env` still works too (e.g. for a
non-interactive/Docker deploy) and acts as the fallback default whenever a
key isn't set in Settings.

Only one is a real secret — the rest are free/no-signup, required only by
usage terms or for higher rate limits:

| Var / Settings field | Needed for | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM keyword translation | Real key needed for good translation. Without it, translation falls back to a naive passthrough — app still runs, just dumber search terms. |
| `DATABASE_URL` | Postgres connection | Pre-filled to match `docker-compose.yml`. Not exposed in Settings — it's infrastructure config, not a per-user key. |
| `UNPAYWALL_EMAIL` | Open-access lookup | Just an email, no signup — but **must be real**: Unpaywall hard-rejects the placeholder `you@example.com` (422 error) and every OA lookup silently fails until you swap it in, degrading full-text links to weaker fallbacks. |
| `OPENALEX_MAILTO` | Faster OpenAlex responses | Just an email, no signup — gets the "polite pool". |
| `NCBI_API_KEY` | PubMed | Optional — raises rate limit 3→10 req/s. |
| `CORE_API_KEY` | Extra full-text PDF coverage | Optional — free key from core.ac.uk; finds institutional-repository copies Unpaywall/OpenAlex miss. |
| `SEMANTIC_SCHOLAR_API_KEY` | (unused currently) | Optional, reserved for future use. |

arXiv, OpenAlex, bioRxiv/medRxiv, Unpaywall, PubMed, and RSS all work with
zero signup.

## Known Limitations (by design, not bugs)

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

## Project Structure

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
    settings_store.py          — Settings-page API key overrides on top of .env
    researcher_enrichment.py  — ORCID + faculty-page scrape
  field_routing.py            — field → source-module mapping
frontend/src/
  pages/                      — one per route
  components/                 — ItemCard, ItemReader, Highlighter, Graph pieces, etc.
.github/workflows/ci.yml       — migrations + live health check (backend), typecheck + build (frontend)
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

## Roadmap

Phase 1 (this build) covers the full spec plus the graph view — see
[`PRD/research-feed-app-spec.md`](PRD/research-feed-app-spec.md). Phase 2
plans (Dockerizing the app itself for always-on self-hosting) are tracked in
[`PRD/rabbit-hole-phase2-roadmap.md`](PRD/rabbit-hole-phase2-roadmap.md).

## Contributing

This started as a personal, single-user tool, not a project actively
seeking contributors — but issues and pull requests are welcome if something's
broken or you've got an improvement in mind.

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for the full text.
