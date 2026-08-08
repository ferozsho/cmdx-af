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

## Remaining Gaps (2026-08-08 — all previous gaps now closed)

The 2026-08-07 gap list has been worked through. Status of each original gap:

| Area | 2026-08-07 gap | Status |
|------|----------------|--------|
| Auth | No auth endpoints/middleware | ✅ register/login/JWT + `get_current_user` + per-user scoping |
| Auth depth | No refresh tokens / revocation / RBAC | ✅ token revocation (password change bumps `token_version`, JWT `ver` checked), `role` column + admin-gated Settings (`get_current_admin`), **all** project sub-endpoints (rag/files/git/validate-path/reindex) now require auth |
| Frontend auth | No logout / change-password UI | ✅ header ⏻ Sign out + Settings "Change Password" card (revokes all sessions) |
| Local agent chunker | hardcoded chunk_size/overlap | ✅ `rag_reindex` now receives `chunk_size`/`chunk_overlap` from Settings; indexer caches them for watcher/startup indexes (native agent needs a restart to pick up) |
| Dockerized local agent | untested | ✅ smoke-tested live (WSS connect, Qdrant, watcher, index) |
| Test coverage | sparse | ✅ 24 API tests (auth guards, RBAC, offline degradation, JWT, hashing) + 9 local-agent tests |
| Rollback / confirmation modal | missing | ✅ `POST /projects/{id}/git/rollback` + UI |
| Path validation + stack detection | missing | ✅ `validate-path` via local agent + auto-detection |
| Dashboard / workspace real data | mock | ✅ real API-backed |
| DB usage | dormant | ✅ all tables read/written, alembic-managed |
| Agents | stubs | ✅ all 11 real LLM |
| RAG vector search | keyword-only | ✅ Qdrant |
| Watcher wiring | not started | ✅ wired + ignore list |

## Known Remaining Work (2026-08-08)

| Area | Gap |
|------|-----|
| Refresh tokens | JWT access tokens only (24h) — no refresh-token rotation endpoint yet |
| Native agent restart | The running native `agentforge start` daemon predates the chunk-settings wiring; restart it to activate (watcher/startup index then uses Settings chunk size/overlap) |
| Frontend auth polish | No "forgot password" / email verification; role is admin/user only |
| Chunker parity | Local agent defaults (50/10) differ from cloud defaults (500/50) until the first Settings-driven reindex sets them |
| Prototype visual parity | Dark theme design system differs from the static `docs/index.html` light prototype — informational only |

---

## Superseded Detail (historical — 2026-08-07)

The original per-page tables (Dashboard, New Project, Live Workspace, RAG
Manager, Git History, Observability, Architecture, Settings, API endpoints,
DB usage, agents, local agent, frontend) and the P0–P3 priority summary all
predate Batches A–E. Every row they listed has since been implemented and
verified. The current state is summarized above and in `docs/NEXT_PLAN.md` +
`docs/CURRENT_IMPLEMENTATION_AUDIT.md`.

