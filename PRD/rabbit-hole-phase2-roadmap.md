# Rabbit Hole — Phase 2 Roadmap

Build after Phase 1 (local, single-user, Postgres) is running and validated over the ~2-week test period. Do not start these alongside Phase 1 — they change the DB schema and app architecture meaningfully enough to warrant a clean second pass.

---

## 1. Flexible split-pane (notes-as-second-pane)

Phase 1 already has:
- Side-by-side reading (#13): paper/article + paper/article
- Highlight & annotate (#10): notes tied to a specific paper

Phase 2 addition: let the second pane be a **flexible slot** — paper, article, or a running/free-form notes doc — user picks per session. This is distinct from #10 (source-anchored highlights); it's an open synthesis space that persists across whatever's open in pane one. Reuses existing notes infrastructure, just decouples the UI slot from "must be a document."

---

## 2. Separate database for sources

Split the `sources` table (custom RSS feeds/journals/sites the user adds) into its own dedicated DB, separate from the core papers/articles/researchers/notes/graph DB. Motivation: sources config is low-volume, rarely-changing, user-management data — different access pattern and lifecycle than the high-volume content tables. Clean separation now avoids migration pain if sources ever need independent backup/sync/sharing later (e.g. sharing a source list between users once multi-user exists).

---

## 3. User login + own-domain hosting

The big one — turns Rabbit Hole from a single-user local/NAS tool into a real multi-user service.

Requires:
- Auth system (sessions or JWT — pick based on whether this stays self-hosted-only or could ever go public)
- Per-user data isolation across every table (papers/articles can likely stay shared/global since they're pulled from public APIs, but lists, notes, highlights, graph edges, reading status, and saved/bookmarked state must be scoped per-user)
- Schema migration: add `user_id` foreign keys throughout
- Domain + hosting setup (reverse proxy, TLS, DNS) — separate infra task from the app code itself
- Decide: multi-tenant single deployment (one instance, many users) vs. each user self-hosts their own instance and login is just local auth. This decision changes the auth architecture significantly — resolve before starting.

---

## 4. Cross-platform desktop releases via GitHub Actions

Same pattern as `t-veera/folio`: build matrix for Windows/Mac/Linux, packaged via Electron (or equivalent, depending on what shape the frontend takes by then), auto-published to GitHub Releases. Only makes sense once the app's core UX is stable — no point packaging something still actively changing shape.

---

## Sequencing note

#2 is low-effort, can go first whenever convenient. #3 and #4 are bigger architectural decisions and should be scoped together, since whether the app is single-user-self-hosted-per-person vs. one shared multi-tenant deployment changes both the auth design (#3) and whether desktop packaging (#4) even makes sense (a multi-tenant web service doesn't need a desktop app; a self-hosted-per-user model does).
