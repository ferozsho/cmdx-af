# AI Agent Framework (AgentForge) — Implementation Plan & System Architecture

## 1. Executive Summary & Repository Analysis

### Current Repository State
- **Repository Path**: `/home/administrator/cmdx-af`
- **Current Files**: Implemented cloud API, web control plane, local agent,
  shared protocol, migrations, tests, and deployment configuration.
- **Status**: Phases 1–7 completed and verified on 2026-08-11. Later phases
  remain tracked separately below.

### Architectural Vision
AgentForge is an enterprise-grade, agentic software development platform designed with a hybrid architecture:
- **AgentForge Cloud (Control Plane)**: Next.js frontend + FastAPI backend +
  PostgreSQL + Redis + durable SQL worker + LLM Provider Layer + Agent
  Orchestrator + Tool Gateway.
- **AgentForge Local Agent (Execution Plane)**: Lightweight Python daemon running on developer workstations. Connects via outbound WSS (port 443) to the Tool Gateway. Executes filesystem CRUD, Git commands, local tests, linters, builds, and local RAG vector indexing directly on local project directories (e.g., `D:\Projects\...` or `/home/user/projects/...`).

---

## 2. Monorepo Repository Structure

```
cmdx-af/
├── apps/
│   ├── web/                        # Next.js 16+ App Router Frontend (SaaS Control Plane)
│   │   ├── app/                    # Pages & Layouts (Dashboard, Workspaces, Devices, RAG, Git, Settings)
│   │   ├── components/             # UI Components (shadcn/ui, Monaco Editor, Live Agent Consoles)
│   │   ├── lib/                    # API Client, SSE handler, Utils
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── api/                        # FastAPI Backend Service (Cloud Brain)
│   │   ├── app/
│   │   │   ├── api/                # REST Routes (projects, devices, instructions, rag, git, llm)
│   │   │   ├── core/               # App Configuration, DB Session, Security, Exceptions
│   │   │   ├── models/             # SQLAlchemy ORM Models (projects, devices, workspaces, instructions, runs, artifacts)
│   │   │   ├── repositories/       # Database Access Layer
│   │   │   ├── services/           # Business Logic Services
│   │   │   ├── llm/                # DeepSeek, OpenAI, Gemini, Claude, Mock
│   │   │   ├── agents/             # CrewAI / Custom Agents (Planning, Arch, UI/UX, Frontend, Backend, DB, Test, Validation, Git)
│   │   │   ├── tools/              # Cloud Tools & Tool Gateway Routing
│   │   │   │   └── gateway/        # Governed WSS routing to Local Agents
│   │   │   ├── worker.py           # Durable SQL-backed pipeline processor
│   │   │   └── wss/                # WebSocket Manager for Local Agent Connections & Event Dispatching
│   │   ├── alembic/                # DB Migrations
│   │   ├── tests/                  # Pytest Unit & Integration Tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── local-agent/                # AgentForge Local Execution Daemon
│       ├── agentforge_local/
│       │   ├── connection/         # Pairing, outbound WSS, reconnect logic
│       │   ├── filesystem/         # Safe File CRUD & Path Isolation
│       │   ├── git/                # Git Branching, Commits, Diffs & Rollbacks
│       │   ├── execution/          # Whitelisted Tool Execution (pytest, npm, ruff, mypy)
│       │   ├── rag/                # Local Code Chunker, Embedder & Qdrant Search
│       │   ├── security/           # Secret Redaction (.env, API keys) & Path Traversal Guard
│       │   ├── workspaces/         # Authorized Workspace Directory Manager
│       │   └── watcher/            # File System Watcher for Real-time RAG re-indexing
│       ├── tests/                  # Local Agent Unit & Security Tests
│       ├── pyproject.toml
│       └── README.md
│
├── packages/                       # Shared Contracts & Protocols
│   └── protocol/                   # Shared JSON-RPC Schemas and Data Models
│
├── docs/                           # Architecture, Specs & API Docs
│   └── IMPLEMENTATION_PLAN.md
│
├── infrastructure/                 # Docker Compose & Configuration
│   ├── docker-compose.yml
│   └── nginx.conf
│
├── .env                            # VM runtime configuration (not committed)
├── Makefile                        # Convenient Build & Run Shortcuts
└── README.md
```

---

## 3. System Components & Key Responsibilities

### 3.1 Cloud Control Plane (`apps/api` & `apps/web`)
1. **Authentication & Authorization**: Device pairing with one-time 8-character pairing codes, device tokens, session management.
2. **Device & Workspace Registry**: Manages registered developer PCs (`devices`), authorized local paths (`workspaces`), and cloud projects.
3. **LLM Provider Gateway**: Unified interface supporting DeepSeek (`deepseek-chat`, `deepseek-coder`), OpenAI, and local endpoints. Includes cost tracking and token usage logging.
4. **Multi-Agent Orchestrator**: Manages sequential/parallel agent execution flow:
   - **Planning Agent**: Analyzes task, queries RAG, produces JSON implementation plan.
   - **Architecture Agent**: Checks architectural boundaries and design patterns.
   - **UI/UX Agent**: Creates UI specifications, layout plans, design system token alignment.
   - **Frontend Agent**: Generates React / Next.js pages, components, hooks.
   - **Backend Agent**: Generates FastAPI routes, services, schemas.
   - **Database Agent**: Generates SQLAlchemy models & Alembic migrations.
   - **Documentation Agent**: Updates project documentation (`README`, `API.md`).
   - **Test Agent**: Generates backend and frontend tests.
   - **Validation Agent**: Runs linting (`Ruff`, `ESLint`), type checks (`mypy`, `tsc`), security scans (`Bandit`).
   - **Git Agent**: Manages isolated feature branches (`agent/{instruction_id}`) and commits.
5. **Tool Gateway**: Distributes tool requests to either Local Agent WSS channels or Cloud Sandboxes transparently.
6. **SSE Event Engine**: Broadcasts real-time pipeline events (agent status, file changes, terminal logs) to web clients via Redis Pub/Sub.

### 3.2 Local Agent (`apps/local-agent`)
1. **Outbound WSS Connection**: Initiates encrypted WSS connection to Cloud (`wss://<domain>/ws/devices`). No open inbound ports or port forwarding required.
2. **Path Isolation & Security**: Enforces strict boundaries around authorized local workspace roots. Blocks traversal (`..`), access to `.env`, `.git/`, SSH keys, and system directories.
3. **Secret Redaction**: Scans file contents and tool outputs for sensitive patterns (API keys, passwords, bearer tokens) before returning data to the Cloud.
4. **Local Tool Sandbox**: Executes whitelisted build, test, and lint commands in non-shell subprocess arrays.
5. **Local RAG & Chunker**: Uses `sentence-transformers` and Qdrant (local vector DB) to chunk and index codebase files (`.py`, `.ts`, `.tsx`, `.md`, `.json`, etc.).
6. **Git Operations Manager**: Operates directly on local `.git` repositories to create isolated branches, record structured commits, compute diffs, and perform safe rollbacks.

---

## 4. Phase-by-Phase Implementation Roadmap

### Phase 0: Repository Analysis & Architecture Specification [COMPLETED]
- [x] Inspect existing workspace.
- [x] Create comprehensive `docs/IMPLEMENTATION_PLAN.md` with hybrid Cloud/Local architecture.

### Phase 1: Foundation & Base Monorepo Scaffolding
- [x] Initialize monorepo directory layout (`apps/web`, `apps/api`, `apps/local-agent`, `infrastructure`).
- [x] Create `docker-compose.yml` for PostgreSQL, Redis, Qdrant, FastAPI,
  durable background execution, and Next.js. The production implementation
  uses a database-backed worker with atomic claims, retries, heartbeats, and
  crash recovery instead of the originally proposed Celery queue.
- [x] Load deployment configuration and secrets exclusively from the root
  `.env` file; example or alternate environment files are intentionally not
  used by this VM deployment.
- [x] Implement FastAPI baseline application with CORS, health/readiness
  endpoints, and database models.

### Phase 2: Local Agent Foundation & Protocol
- [x] Build `apps/local-agent` package structure.
- [x] Implement typed JSON messages for WSS tool invocation (`tool_request`,
  `tool_result`, `heartbeat`, and pairing contracts).
- [x] Build the device pairing flow with durable, hashed, one-time
  eight-character codes and local-agent token exchange.
- [x] Build the authenticated Cloud WSS Device Gateway, heartbeat persistence,
  and request/result Connection Manager in `apps/api/app/wss`.

### Phase 3: Database Models & Alembic Migrations
- [x] Define SQLAlchemy ORM models: `User`, `Device`, `Workspace`, `Project`,
  `Instruction`, `AgentRun`, `Artifact`, `FileOperation`, `GitCommit`,
  `LLMUsage`, and the durable `BackgroundJob` successor to `LocalJob`.
- [x] Configure Alembic, maintain the complete migration chain, enforce
  instruction ownership, and verify zero model/schema drift.
- [x] Implement validated Pydantic request/response schemas and repository
  data-access classes for the core aggregates.

### Phase 4: Tool Gateway & Local Execution Tools
- [x] Implement Tool Gateway abstraction in Cloud API (`apps/api/app/tools/gateway`).
- [x] Implement Local Agent Filesystem tools (`read_file`, `write_file`,
  `update_file`, `delete_file`, `list_files`, `get_project_tree`,
  `search_in_files`).
- [x] Implement Local Agent security rules (path isolation, traversal and
  symlink protection, sensitive-file blocking, secret redaction, output and
  execution bounds).
- [x] Implement Local Agent command tools (`run_tests`, `run_linter`,
  `run_formatter`, `run_type_check`, `run_build`) with independent task
  restrictions and non-shell command arrays.
- [x] Implement Local Agent Git tools (`git_status`, `git_branch`, `git_diff`,
  `git_commit`, `git_rollback`).

### Phase 5: Local RAG & Vector Storage
- [x] Implement local Code Scanner and Chunker in `apps/local-agent/agentforge_local/rag`.
- [x] Integrate the persisted Qdrant vector database with server/client
  compatibility and scoped stale-vector cleanup.
- [x] Implement semantic code search (`rag_search`) returning bounded top-K
  results with similarity scores, file paths, and line ranges.
- [x] Implement file system watcher re-indexing for create, modify, delete,
  and move events.

### Phase 6: LLM Provider Abstraction Layer
- [x] Build the provider interface in `apps/api/app/llm/base.py` supporting
  chat completions, typed streaming, strict structured JSON output, bounded
  transient retries, and cost calculation.
- [x] Implement the DeepSeek API provider (`deepseek-chat`, `deepseek-coder`).
- [x] Implement Mock Provider for explicit offline testing (`APP_MODE=mock`).
- [x] Implement Model Router and durable, redacted token/usage tracking for
  completion and streaming calls.

### Phase 7: Multi-Agent System & Sequential Pipeline
- [x] Implement individual specialized agent modules:
  - Planning Agent
  - Architecture Agent
  - UI/UX Agent
  - Frontend Agent
  - Backend Agent
  - Database Agent
  - Documentation Agent
  - Test Agent
  - Validation Agent
  - Git Agent
- [x] Implement the durable sequential orchestration engine with ordered
  agents, persisted checkpoints, resume behavior, bounded job retries,
  cancellation, failure stops, and human approval pauses.

### Phases 1–7 Verification Evidence (2026-08-11)

- API test suite: 69 passed.
- Local-agent test suite: 33 passed inside the final CPU-only image.
- Alembic upgrade: current at `l8g9h0i1j2k3`; `alembic check` reports no
  upgrade operations.
- Python Ruff and bytecode compilation: clean across API, migrations, local
  agent, tests, and shared protocol.
- Web TypeScript check and optimized Next.js build: passed.
- Web ESLint: zero errors and 90 warnings; warning cleanup remains quality
  debt outside the Phase 1–7 acceptance scope.

### Phase 8: SSE Event Infrastructure & Real-time Broadcasting
- [ ] Set up Redis Pub/Sub event dispatcher in FastAPI.
- [ ] Implement SSE endpoint (`GET /api/v1/projects/{id}/stream`).
- [ ] Connect agent lifecycle events, file CRUD notifications, and terminal outputs to the event stream.

### Phase 9: Frontend Web Application
- [ ] Set up Next.js 16+ App Router project with Tailwind CSS, shadcn/ui components, and Lucide icons.
- [ ] Build Dashboard screen (project statistics, active pipelines, recent activity).
- [ ] Build Device Management screen (`/devices`) with device pairing UI.
- [ ] Build Project Creation Wizard with Local Machine vs Cloud Workspace selection.
- [ ] Build Project Workspace screen:
  - Instruction submission prompt
  - Live Agent Execution pipeline cards
  - Live SSE Event Console
  - File Tree Browser & Monaco Code Diff Viewer
  - RAG Manager screen
  - Git History & Rollback UI
  - Test & Validation Status screen

### Phase 10: Testing, Hardening & End-to-End Verification
- [ ] Run end-to-end acceptance workflow:
  1. Pair Local Agent with Cloud Control Plane.
  2. Create Project targeting local directory.
  3. Index local repository with RAG.
  4. Submit instruction ("Create payment management module").
  5. Validate full agent execution sequence, local file generation, automated tests, linting, and local Git commits.
- [ ] Verify safety constraints (E501 line length < 100 in Python code, zero secret leaks, zero path traversal).
- [ ] Perform linting (`Ruff`, `ESLint`), type checking (`mypy`, `tsc`), and test pass verification.
