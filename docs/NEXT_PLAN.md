# AgentForge — Next Implementation Plan

**Date:** 2026-08-08
**Status:** Current, verified against codebase

---

## 0. Verified Current State

Everything below is confirmed working **REAL** (not mock) as of 2026-08-08:

| Area | Status |
|------|--------|
| Projects CRUD (DB-backed) + path validation + stack detection | ✅ |
| New Project → `initial_instruction` persisted + pipeline kicked off | ✅ |
| Devices: list, pairing code, **revoke** (`DELETE /devices/{id}`) | ✅ |
| RAG Manager: search, stats, **re-index** (`rag_reindex` local tool) | ✅ |
| Observability: health/full + **real agent metrics** (`/observability/agent-metrics`, AgentRun persisted per run) | ✅ |
| Artifacts: persisted per agent + **dedicated API** (`GET /projects/{id}/artifacts`) | ✅ |
| DiffViewer: real git-HEAD baseline (`git_show_file`) + LCS diff | ✅ |
| VisualAnalysisAgent: real PNG/JPEG byte parsing (dims, dominant colors) | ✅ |
| Settings: persisted to `apps/api/data/runtime_settings.json` + `api_data` volume | ✅ |
| TestAgent / ValidationAgent: write files, run pytest/ruff/mypy/bandit/eslint | ✅ |
| SSE live stream, WSS Tool Gateway, local agent tools | ✅ |

### Known bug (found during audit)
- `git_agent.py` calls `git_checkout_branch` with `arguments={"branch": ...}` but the local handler reads `args["branch_name"]` → **KeyError**, branch creation silently fails (commit still works).

---

## 1. Design Constraint: Local Agent Offline

The RAG / artifacts / file-baseline / file-content / git endpoints all route through
`ToolGateway → WSS → local agent`. When no workstation is connected:

- `ToolGateway.send_tool_request` returns `success=False` with `"Device ... is offline."`
- Today several endpoints convert that into **HTTP 500** (`rag/search`, `files/content`,
  `files/original`, `git/status`, `git/log`, `tree`).
- The frontend then shows a generic error box.

**Target behavior (graceful degradation):**
1. API returns **HTTP 200 with a structured `{status: "offline", detail: "..."}`** payload
   (or a `503` with a machine-readable body) instead of a raw 500.
2. Frontend shows an **"Agent offline — connect a workstation"** state (banner/empty state
   with pairing link), not a red error toast.
3. RAG stats already returns zeros offline — keep that, add an `online: bool` flag.

---

## 2. Prioritized Work Items

### P1 — Core functional gaps
- [x] **1.1 Git rollback (endpoint + UI).** Added `POST /projects/{id}/git/rollback`
      (uses existing `git_rollback` local tool), `rollbackGit()` in `apps/web/lib/api.ts`,
      and a ⏪ Rollback button with confirm on every commit in `apps/web/app/git/page.tsx`.
- [x] **1.2 Fix `git_agent.py` branch bug** (`branch` → `branch_name`).
- [x] **1.3 Dashboard real stats.** `GET /projects/stats/summary` now aggregates real
      `agent_runs` count (COMPLETED) and sums `tests_passed` from Test Agent metadata.
- [x] **1.4 Instruction lifecycle.** Pipeline marks instructions `COMPLETED`/`FAILED`
      after the run; added `GET /projects/{id}/instructions` + `listInstructions()` client.

### P2 — Persistence & observability depth
- [x] **2.1 LLM usage tracking.** New `app/llm/tracking.py` `UsageTrackingProvider`
      wraps every provider (via `ModelRouter`); pipeline sets a contextvar with the
      instruction id; each call persists an `llm_usage` row in a background task.
- [x] **2.2 Git commit logging.** `git_agent.py` persists a `git_commits` row on commit.
- [x] **2.3 File operation logging.** `BaseAgent._write_files` logs every write to
      `file_operations`.
- [x] **2.4 Observability UI.** `GET /observability/agent-metrics` now returns
      `llm_usage` aggregates (calls, tokens, cost, models); Observability page has a
      new "LLM Usage" panel.

### P3 — Offline resilience (user-flagged)
- [x] **3.1 API graceful-degradation helper.** `_tool_is_offline()` + `_offline_response()`
      in `projects.py`; all tool-backed endpoints return a structured
      `{status:"offline", online:false, detail}` (HTTP 200) instead of 500 when the
      device is offline. `rag/stats` now includes `online`.
- [x] **3.2 Frontend offline states.** RAG page shows an amber "workstation offline"
      banner + disables search/re-index; Git History shows an offline banner and guards
      the branch card; workspace client handles offline for file tree, file content,
      baseline, git status (GIT tab), and RAG search.
- [x] **3.3 RAG page**: `online` flag disables search/re-index when offline.

### P4 — Platform hardening (larger — COMPLETED 2026-08-08)
- [x] **4.1 Qdrant vector search.** New `agentforge_local/rag/qdrant_store.py`
      (collection per workspace, cosine, 384-d) + `LocalRAGIndexer` now upserts
      into Qdrant and searches vectors first, falling back to keyword search
      when Qdrant is unreachable. Verified live against `localhost:6333`.
- [x] **4.2 File watcher wiring.** `agentforge start` now watches all registered
      workspaces via `WorkspaceWatcher` (watchdog) and auto re-indexes RAG on
      file changes (5s debounce).
- [x] **4.3 Pairing/auth exchange.** Cloud: pairing codes stored + expiry,
      `POST /devices/pair` (code → device + `device_token` in capabilities),
      `POST /devices/validate-token`, WSS `/ws/devices/{id}` validates `?token=`.
      Local agent: `agentforge connect <code>` exchanges credentials to
      `~/.agentforge/device.json`, WSS client sends the token. Legacy devices
      (no token) still connect.

---

## 3. Edit Project Modal (requested 2026-08-08)

- **Large modal**: `max-w-[860px]`, Name + Description side-by-side.
- **Local Workspace Path field** (LOCAL targets) with a **Check Folder** button
  using `POST /projects/validate-path` (inline validity, files/dirs, git, detected
  stack, warnings). `local_path` is now a real Project column
  (`alembic/versions/c7d8e9f0a1b2_add_project_local_path.py`) exposed in
  `GET/POST/PATCH /projects` and shown on dashboard cards.
- **Auto RAG with progress bar (click-and-forget)**: `POST /projects/{id}/rag/reindex`
  now starts a **background job** (returns immediately) and
  `GET /projects/{id}/rag/reindex-status` is polled by the modal — animated
  progress bar → ✓ done (auto-close) or ✗ failed (retry). User can close anytime;
  indexing continues server-side. RAG Manager re-index uses the same background
  job + progress bar.

---

## 4. Deployment Note (2026-08-08)

The Docker containers (`agentforge-api`, `agentforge-web`) were **not** rebuilt
during this work (per workflow constraints). The running containers still serve
pre-change code (no `/observability/agent-metrics`, no `online` flag, no rollback
endpoint). To activate all batches A–E + the modal:

```bash
docker compose -f infrastructure/docker-compose.yml build api web
docker compose -f infrastructure/docker-compose.yml up -d api web
# then apply the new migration (inside the api container):
docker exec agentforge-api alembic upgrade head
```

The local agent daemon is confirmed **online** in dev (RAG stats returned 1 file
/ 1248 chunks), and Qdrant vector search is verified working against
`localhost:6333`.
