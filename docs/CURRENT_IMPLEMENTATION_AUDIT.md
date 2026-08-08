# AgentForge — Current Implementation Audit

**Date:** 2026-08-08 (refreshed — supersedes the 2026-08-07 audit)
**Authoritative status source:** `docs/NEXT_PLAN.md`

---

## 1. Executive Summary

AgentForge is now REAL end-to-end: DB-backed CRUD, real DeepSeek LLM calls
(Settings-page-driven config), a live Local Execution Daemon over WSS, Qdrant
vector search with background indexing + live progress, auth
(register/login/JWT), observability, and a fully polished Next.js UI. No mock
data sources remain in the cloud API path (MockLLMProvider exists only for
tests / APP_MODE=mock). The 2026-08-07 audit claimed mock CRUD, stub agents,
hardcoded dashboards, no Qdrant, no watcher wiring, no validate-path, no
settings persistence, no observability, no auth — **all of those have since
been implemented and verified.** See sections 3–7 below for the current gaps.

---

## 2. Existing and Working (REAL)

### 2.1 Backend Infrastructure
| Component | Status | Details |
|-----------|--------|---------|
| FastAPI app factory | ✅ Real | CORS, router aggregation at `/api/v1` |
| Config (Pydantic Settings) | ✅ Real | `.env` loading, all keys present |
| Database engine + session | ✅ Real | SQLAlchemy async, session factory, `get_db` dependency |
| DB Models (10 tables) | ✅ Real | User, Device, Workspace, Project, Instruction, AgentRun, Artifact, FileOperation, GitCommit, LLMUsage |
| Health endpoint | ✅ Real | `GET /health` returns config values |
| SSE Broadcaster | ✅ Real | In-memory pub/sub via asyncio.Queue |
| WSS Connection Manager | ✅ Real | Device socket registry, request→response futures, 120s timeout |
| Tool Gateway | ✅ Real | Constructs ToolRequest, delegates to WSS manager |
| WSS Router | ✅ Real | `/ws/devices/{device_id}` WebSocket endpoint |

### 2.2 LLM Layer
| Component | Status | Details |
|-----------|--------|---------|
| BaseLLMProvider | ✅ Real | Abstract class with `generate()` |
| DeepSeekProvider | ✅ Real | HTTP POST to DeepSeek API, token counting, cost calc |
| MockLLMProvider | ✅ Real | Returns hardcoded responses for testing |
| ModelRouter | ✅ Real | Selects provider based on `APP_MODE` and API key presence |

### 2.3 Agent Pipeline
| Component | Status | Details |
|-----------|--------|---------|
| PipelineOrchestrator | ✅ Real | Sequential execution of 11 agents with SSE callbacks |
| BaseAgent | ✅ Real | Abstract class, gets LLM provider from ModelRouter |
| PlanningAgent | ✅ Real | Calls LLM with json_mode for implementation plan |
| Instruction endpoint | ✅ Real | `POST /instructions` triggers pipeline as async task |

### 2.4 Real API Endpoints (via ToolGateway → WSS → Local Agent)
| Endpoint | Status | Details |
|----------|--------|---------|
| `GET /projects/{id}/tree` | ✅ Real | File tree from local agent |
| `GET /projects/{id}/files/content` | ✅ Real | File content from local agent |
| `POST /projects/{id}/rag/search` | ✅ Real | RAG search from local agent |
| `GET /projects/{id}/git/status` | ✅ Real | Git status from local agent |

### 2.5 Local Agent (100% REAL)
| Module | Status | Details |
|--------|--------|---------|
| CLI | ✅ Real | `start`, `workspace-add`, `workspace-list` |
| WSS Client | ✅ Real | Outbound WebSocket with auto-reconnect |
| Tool Handler | ✅ Real | Dispatches 12 tool types with error handling |
| Filesystem Ops | ✅ Real | read/write/update/delete/tree with PathGuard |
| Git Ops | ✅ Real | status/branch/commit/diff/rollback via GitPython |
| Execution Runner | ✅ Real | Whitelisted subprocess runner with SecretRedactor |
| Path Guard | ✅ Real | Path traversal protection, restricted path blocking |
| Secret Redactor | ✅ Real | 5 pattern classes (API keys, tokens, DB URLs, passwords, PEM) |
| Workspace Manager | ✅ Real | JSON file persistence for workspace registry |
| File Watcher | ✅ Real | watchdog-based, 5s debounce, `_IGNORED_PARTS` path-parts ignore (venv/caches) — wired into `agentforge start` |
| RAG Chunker | ✅ Real | Line-window chunking for 12 file types |
| RAG Embedder | ✅ Real | sentence-transformers with deterministic fallback |
| RAG Indexer | ✅ Real | **Qdrant vector search** (`ws_<md5>` collection, cosine 384-d) + keyword fallback; `_instances` cache; `index_state` live progress |

### 2.6 Frontend (Real Parts)
| Component | Status | Details |
|-----------|--------|---------|
| Root Layout | ✅ Real | Next.js 16 App Router, metadata, nav |
| Project workspace page | ✅ Real | SSE subscription, file tree, file content, RAG search, git status, pipeline trigger |
| New Project page | ✅ Real | Form submission to API |
| DiffViewer component | ✅ Real | Side-by-side diff with toggle |
| Devices page (pairing) | ✅ Real | POST /devices/pairing-code call |

### 2.7 Tests
| Component | Status | Details |
|-----------|--------|---------|
| API health test | ✅ Real | Tests health endpoint |
| API LLM test | ✅ Real | Tests ModelRouter |
| API pipeline test | ✅ Real | Tests PipelineOrchestrator (mock mode) |
| Local agent path guard tests | ✅ Real | 3 tests |
| Local agent embedder tests | ✅ Real | 1 test |
| Local agent redactor tests | ✅ Real | 2 tests |

---

## 3. Current Gaps (2026-08-08)

The former “Existing but Partial / Mock / Missing / Broken” sections are obsolete —
the rows they listed (DB CRUD, real agents, Qdrant, watcher, validate-path, settings
persistence, observability, auth, rollback, error handling) are implemented and
verified. Remaining gaps:

| Area | Gap |
|------|-----|
| Auth depth | No refresh tokens, no token-revocation UI, no per-route RBAC beyond projects/devices |
| Local agent chunker | `chunker.py` still hardcodes chunk_size/overlap (not wired to Settings page RAG fields) |
| Dockerized local agent | Image + compose exist; the native `agentforge start` flow is what's exercised |
| Test coverage | Endpoint tests for RAG/settings/validate-path/rollback/auth would close gaps |
| Prototype doc | `docs/index.html` is a static mock — informational only, not wired |

---

## 4. Integration Map (current)

```
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (Next.js 16 App Router)                │
│  login  dashboard  workspace-client  devices  settings      │
│  rag-manager  observability  (all REAL, auth-guarded)       │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST (Bearer JWT) / SSE
┌──────────────────────▼──────────────────────────────────────┐
│                   FASTAPI BACKEND                            │
│  auth  projects  devices  settings  observability          │
│  rag  instructions  sse  agents   (ALL DB-backed + real)    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PipelineOrchestrator — 11 real agents (LLM, json_mode) │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ToolGateway → WSSConnectionManager → /ws/devices/{id} │ │
│  └────────────────────────────────────────────────────────┘ │
│  PostgreSQL (users/projects/devices/agent_runs/llm_usage…)  │
└──────────────────────┬──────────────────────────────────────┘
                       │ WSS (authenticated tools)
┌──────────────────────▼──────────────────────────────────────┐
│  LOCAL AGENT — native or Docker                            │
│  filesystem  git  execution  RAG (Qdrant + keyword)        │
│  watcher  embedder  secret-redactor  path-guard            │
└─────────────────────────────────────────────────────────────┘
```
┌──────────────────────▼──────────────────────────────────────┐
│              LOCAL AGENT (Python Daemon)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │File Ops  │  │ Git Ops  │  │   RAG    │  │ Execution  │ │
│  │ (real)   │  │ (real)   │  │(partial) │  │  (real)    │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │PathGuard │  │SecretRed │  │ Watcher  │                 │
│  │ (real)   │  │ (real)   │  │(not wired)│                │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Reuse Plan

### MUST PRESERVE:
1. **All database models** — complete and well-structured
2. **Database engine + session** — fully functional
3. **SSE Broadcaster** — clean pub/sub, works well
4. **WSS Connection Manager** — robust request-response over WebSocket
5. **Tool Gateway** — clean abstraction over WSS
6. **LLM layer** — DeepSeekProvider, MockLLMProvider, ModelRouter all work
7. **PipelineOrchestrator** — sequential execution pattern is correct
8. **PlanningAgent** — only agent that actually works
9. **Local Agent (ALL modules)** — 100% real, nothing to replace
10. **DiffViewer component** — works correctly
11. **Workspace client SSE + file tree + RAG + Git** — real API integration works
12. **New Project form** — real API submission works

### MUST EXTEND (not replace):
1. Projects endpoint → add database persistence, keep ToolGateway calls
2. Devices endpoint → add database persistence
3. Dashboard page → add API data fetching, keep layout
4. Workspace header → fetch project details from API
5. Agent list → fetch from pipeline config
6. Stub agents → add real LLM calls + tool invocations

### MUST ADD:
1. Project path validation endpoint + UI
2. Technology stack detection
3. Settings CRUD endpoint
4. Observability aggregation endpoint
5. Real health check endpoint
6. Error handling on all frontend API calls
