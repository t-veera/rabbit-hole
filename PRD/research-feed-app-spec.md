# Rabbit Hole — Build Spec for Claude Code

## Overview
**Rabbit Hole** is a self-hosted research discovery app. User enters plain-language interests (e.g. "dinosaurs and feathers"), the app translates that into real academic search terms, pulls matching papers + science journalism from multiple sources, surfaces researcher profiles, and presents everything in a clean RSS-reader-style UI. Includes a manual/citation graph view (Obsidian-style) and note-taking.

**Phase 1 (now):** Local-only, single-user, Postgres. Runs on localhost for ~2 weeks of testing.
**Phase 2 (later):** Dockerized, deployed to Synology NAS — same Postgres, just containerized, no DB migration needed.

Build Phase 1 only. Structure the code so Dockerization later is straightforward (no localhost-hardcoded assumptions, env-based config, no OS-specific file paths).

---

## Tech Stack
- Backend: Python, FastAPI
- DB: **Postgres** (used directly from the start — no SQLite, no later migration). Run via a local Postgres install or a docker-compose Postgres container even in Phase 1 (recommended: docker-compose just for the DB, keeps Phase 2 migration trivial since it's already containerized). Use SQLAlchemy ORM + Alembic for migrations.
- Frontend: React + Vite
- Styling: plain CSS or Tailwind with a custom design system (see Aesthetic section) — no default component-library look
- Background jobs: APScheduler (in-process) for periodic feed refresh — no need for Celery/Redis at this scale
- Graph rendering: react-force-graph or vis-network

---

## Data Sources & Routing

Translate user's plain-language keywords into search terms via an LLM call (use Claude API), then route to source APIs based on inferred field. Maintain a field→source mapping, e.g.:

- Biology/medicine/genome → PubMed, bioRxiv, medRxiv
- Physics/astronomy/CS/math → arXiv
- General cross-field paper metadata, citations, author info → OpenAlex, Semantic Scholar
- Economics → RePEc, SSRN (where API/RSS available)
- Humanities/politics/general science journalism → curated RSS list (Aeon, Quanta, Nature News, Science News, etc. — user-extensible)

**Search order (critical):** always search the user's own added sources first (see Custom Sources below), then fall back to the broader API set. Tag results with their origin so the UI can show "from your sources" vs "discovered."

**Full text retrieval:**
- Call Unpaywall API (free, no auth required for reasonable volume — just pass a user email as required by their terms) for every DOI to check for a legal open-access copy
- Fall back to arXiv/bioRxiv/medRxiv direct PDF links where the paper originated there
- If no legal OA copy exists, store abstract + publisher link only — do not attempt to circumvent paywalls anywhere in this codebase

**Researcher data:**
- Pull author list, affiliation, and publication history from OpenAlex (has ORCID linkage where available)
- Attempt photo: check ORCID profile first, then attempt a lightweight scrape of the researcher's university faculty page if a URL can be located (search "[name] [affiliation] faculty page"); fall back to initials avatar if nothing found
- Attempt degree: scrape from faculty bio page if found; leave blank if not — do not fabricate
- Corresponding author email: pull from paper metadata where publishers include it (common in PubMed/Crossref records)

---

## Core Features (build all, Phase 1 scope)

1. **Keyword input** — plain language, LLM-translated to real search terms, editable before search runs (show user what it translated to)
2. **Field/topic filters** — filter feed by inferred field (biology, physics, econ, politics, art, etc.)
3. **Custom sources** — user can add specific journals/RSS feeds/sites; these are searched first per topic
4. **Feed view** — chronological, card-based, clean typography, shows title/authors/source/date/OA-availability badge
5. **Paper detail view** — abstract, full text if legally available (embedded reader or link), citation info, author list (clickable)
6. **Researcher profile view** — photo/avatar, affiliation, degree (if found), recent publications list, corresponding email if available
7. **Journalism track** — separate feed tab pulling from curated science-journalism RSS sources, same reading UI
8. **Bookmarks / Favorites / Custom lists** — user-created lists, add papers/articles to any number of lists
9. **Notifications** — in-app indicator for new items matching active topics since last visit (no need for push/email in Phase 1)
10. **Highlight & annotate** — select text in a paper, add a note; notes stored with paper reference, timestamp, and topic tag
11. **Export notes** — filter by date range and/or topic, export as markdown or plain text
12. **Reading status** — unread / read / skimmed, filterable
13. **Side-by-side reading** — open two papers/articles in split-pane view
14. **Digest cadence setting** — per-topic setting for real-time vs daily vs weekly refresh (controls the background job scheduler)
15. **Full-text search** — search across all saved library content (papers, notes, journalism), not just live feed
16. **Citation export** — BibTeX and RIS export for saved papers
17. **Reading queue vs reference library** — two distinct saved states: "to read" (queue, linear) vs "reference" (library, non-linear); a paper can move between or hold both states

### Graph view
- Two node types, visually distinct:
  - **Linked** — connected to ≥1 other node via an edge, regardless of saved status
  - **Saved** — in the user's library, regardless of link status (orphans allowed and shown)
  - A node can be both; render with a combined visual state (e.g. filled + colored border)
- Edges:
  - **Manual** — user explicitly draws a connection between two items (from a saved or unsaved item)
  - **Auto/citation** — derived from OpenAlex citation data (cites/cited-by), rendered in a visually different edge style than manual links, and toggleable on/off as a layer
- Clicking a node opens that paper/article's detail view
- Orphaned saved items should be easy to surface (e.g. a filter toggle: "show only orphans") since the user's workflow is "save now, connect later"

---

## Aesthetic Direction
Reference: Aeon.co and Fifty Two (fiftytwo.in) — editorial, serif-forward reading typography, generous whitespace, restrained color palette, content-first layout with minimal chrome. Explicitly avoid: default Material Design look, default shadcn/Tailwind starter aesthetic, generic SaaS-dashboard card grids, AI-tool-generated purple gradients. Typography should read like a longform publication, not a productivity app. Use a serif for article body text, a clean sans for UI chrome/metadata. Dark mode optional but not required for Phase 1.

---

## Explicitly Out of Scope for This Build
- Any paywall circumvention, ad-blocker-detection bypass, or scraping behind authentication walls (LinkedIn, publisher login walls) — full text only via legal OA routes (Unpaywall, preprints, author-hosted copies)
- Multi-user auth/accounts (single local user for Phase 1)
- Push notifications / email digests (Phase 2+)
- Docker/deployment config (Phase 2 — structure code to make this easy, but don't build it now)

---

## Deliverable
A working local app (`localhost`) with:
- FastAPI backend exposing REST endpoints for search, feed, papers, researchers, lists, notes, graph
- React frontend implementing all Phase 1 features above
- Postgres schema (with Alembic migrations) covering: papers, articles, researchers, sources, lists, notes/highlights, graph edges (manual + cached citation edges), reading status
- docker-compose file for the Postgres service (app itself still runs locally in Phase 1, DB is containerized from day one so Phase 2 needs no DB migration)
- A `.env.example` for API keys and DB connection string (Anthropic API key for keyword translation, Unpaywall contact email, Postgres connection URL, any other source API keys)
- README with setup/run instructions
