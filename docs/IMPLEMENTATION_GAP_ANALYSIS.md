# AgentForge — Implementation Gap Analysis

**Date:** 2026-08-08 (refreshed — supersedes the 2026-08-07 analysis)
**Authoritative status source:** `docs/NEXT_PLAN.md`

---

## Status: 2026-08-08

This analysis was originally written before Batches A–E landed. Nearly every
row below was ⬜/🔴 at that time; they are now **implemented and verified**:

- **Dashboard**: real KPIs (`GET /projects/stats/summary`), DB-backed project
  cards, per-project RAG indexing progress, in-flow Edit/Delete.
- **New Project**: DB-backed create, local path + `POST /projects/validate-path`
  (delegates to local agent), auto stack detection, auto-RAG with background
  reindex + progress bar.
- **Live Workspace**: SEO-friendly tab URLs, real project header/device/path,
  live agent pipeline with real statuses, full-height FILES tree (collapsed by
  default, no pagination), DiffViewer with real git-HEAD baseline, RAG tab with
  live progress + pagination + loading/offline/empty states.
- **RAG Manager / Git History / Observability / Architecture / Settings**:
  all real pages exist, API-backed, offline-banner-aware.
- **Backend**: all CRUD is DB-backed; tool endpoints degrade gracefully
  (`{status:"offline", online:false}`) instead of 500s; **auth added**
  (register/login/JWT, protected projects+devices).
- **Database**: all tables read/written; alembic-managed (initial schema +
  `c7d8e9f0a1b2` local_path migration applied).
- **Agents**: all 11 run real LLM calls (json_mode coerced via `_content_dict`);
  runs/artifacts persisted.
- **Local agent**: Qdrant vector search (per-workspace `ws_<md5>` collection),
  watcher wired with ignore list, silent embedding, `_IGNORED_PARTS` covers
  venv/caches.

## Remaining Gaps (2026-08-08)

| Area | Gap |
|------|-----|
| Auth depth | No refresh tokens / token revocation UI / RBAC beyond projects+devices |
| Local agent chunker | `chunker.py` hardcodes chunk_size/overlap — not wired to Settings RAG fields |
| Dockerized local agent | Image + compose exist; native flow is what's exercised |
| Test coverage | Add endpoint tests (auth, RAG, settings, validate-path, rollback) |
| Frontend auth | Login page + AuthGuard done; no "change password"/"logout" UI yet |

---

## Superseded Detail (historical — 2026-08-07)

The per-page tables below (Dashboard, New Project, Live Workspace, RAG Manager,
Git History, Observability, Architecture, Settings, API endpoints, DB usage,
agents, local agent, frontend) all predate Batches A–E. Treat them as the
"before" snapshot; the current state is summarized above and in
`docs/NEXT_PLAN.md` + `docs/CURRENT_IMPLEMENTATION_AUDIT.md`.

| Rollback button | ⬜ | Missing |
| Confirmation modal | ⬜ | Missing |
| Visual design vs prototype | 🔴 | Different layout entirely |

---

## 4–13. Superseded per-page tables (2026-08-07)

The original document's sections 4–13 (RAG Manager, Git History, Observability,
Architecture, Settings, API endpoints, Database usage, Agents, Local Agent,
Frontend general) are intentionally removed — every row is now implemented and
verified. See the "Status: 2026-08-08" summary at the top of this file and
`docs/NEXT_PLAN.md` for the authoritative record.

| Empty states | ⬜ | No "no projects" messages |
| TypeScript types for API | ⬜ | No shared types |
| Environment config | ⬜ | API URL hardcoded |
| Responsive design | 🟡 | Basic responsive, not matching prototype breakpoints |
| Visual design system | 🔴 | Dark theme vs prototype's light theme |
| Prototype visual parity | 🔴 | Different colors, spacing, components |

## 14. Priority Summary

### P0 (Blocking — Fix Immediately)
1. Project path validation endpoint + UI
2. Database-backed project CRUD
3. Database migrations setup (Alembic)

### P1 (Core Functionality)
4. Real dashboard data from API
5. Real workspace header from API
6. Database-backed device CRUD
7. All frontend pages matching prototype layout

### P2 (Agent Pipeline)
8. Stub agents → real LLM implementations
9. Real test execution via local agent
10. Real validation via local agent
11. Real git operations via local agent
12. RAG vector search (Qdrant integration)

### P3 (Polish)
13. Observability page + metrics aggregation
14. Settings page + CRUD
15. Architecture page
16. RAG Manager page
17. Git History page
18. Pixel-perfect visual matching to prototype
19. Loading/empty/error states everywhere
20. Responsive design polish
