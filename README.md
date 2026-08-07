# AgentForge — AI Agent Framework

AgentForge is an enterprise-grade, multi-agent software development platform designed with a hybrid architecture:
- **AgentForge Cloud Control Plane**: Next.js 16+ Web UI + FastAPI backend + PostgreSQL + Redis + Qdrant + LLM Provider Layer + Multi-Agent Orchestrator.
- **AgentForge Local Execution Daemon**: Lightweight workstation daemon running on developer PCs that connects via secure outbound WebSocket (WSS) to perform safe filesystem CRUD, local tests, linters, Git operations, and local RAG indexing directly on local project directories.

---

## 🏗️ Architecture Overview

- **Applications**:
  - `apps/web`: Next.js 16 App Router Control Plane UI (`http://localhost:3000`).
  - `apps/api`: FastAPI Control Plane API & WSS Tool Gateway (`http://localhost:8000`).
  - `apps/local-agent`: Python Local Execution Daemon (`agentforge_local`).
- **Packages**:
  - `packages/protocol`: Shared JSON-RPC message protocol schemas (`ToolRequest`, `ToolResult`, `AgentEventMessage`, etc.).
- **Infrastructure**:
  - PostgreSQL 16 (Relational metadata)
  - Redis 7 (SSE Pub/Sub & task queue)
  - Qdrant Vector DB (Vector embeddings & semantic code search)

---

## 🚀 Running AgentForge

### Option A: Complete Docker Compose Stack (Recommended)

To run the entire platform (PostgreSQL, Redis, Qdrant, FastAPI API, and Next.js Web UI) in isolated Docker containers:

1. **Copy the Environment File**:
   ```bash
   cp .env.example .env
   ```

2. **Build and Start All Containers**:
   ```bash
   cd infrastructure
   docker compose up -d --build
   ```

3. **Start the Local Execution Agent on Your PC**:
   In a local terminal (outside Docker), start the workstation daemon:
   ```bash
   python -m agentforge_local start
   ```

4. **Access the Web Dashboard**:
   Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

### Option B: Local Development Mode

To run backend services and frontend directly on your host machine for active development:

1. **Set Up Python Virtual Environment & Install Monorepo Packages**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e packages/protocol -e apps/api -e apps/local-agent
   ```

2. **Start FastAPI Cloud API Backend**:
   ```bash
   cd apps/api
   uvicorn app.main:app --reload --port 8000
   ```

3. **Start Local Agent Daemon**:
   In a separate terminal window:
   ```bash
   python -m agentforge_local start
   ```

4. **Start Next.js Frontend Control Plane**:
   In a separate terminal window:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

---

## 💻 Local Agent CLI Commands

The Local Agent daemon (`agentforge_local`) manages authorized project paths on your PC:

```bash
# Register an authorized local project workspace path
agentforge workspace-add prj_demo_001 "D:\Projects\my-app"

# List registered local project workspaces
agentforge workspace-list

# Start outbound WSS daemon
agentforge start
```

---

## 🎯 Usage & Platform Features

### 1. Project Dashboard (`/`)
- Monitor total registered projects, workstation connectivity status (`● FEROZ-PC Online`), daily agent run metrics, and test pass rates.

### 2. Device Management (`/devices`)
- Pair new developer workstations by generating temporary 8-character pairing codes (`AGF-XXXX`).

### 3. Interactive Project Workspace (`/projects/[id]`)
- **AGENTS Tab**: Submit natural language instructions (e.g. *"Create payment management module with FastAPI endpoints, React admin table, unit tests, and git commit"*). Watch the 11 sequential agents execute live with real-time SSE progress streaming.
- **FILES Tab**:
  - Collapsible/expandable directory tree with live file size formatting (`B`, `KB`, `MB`).
  - Real-time Git file status badges (`MODIFIED`, `NEW`, `STAGED`, `UNPUSHED`).
  - Directory change indicators (`●`) highlighting subtrees containing uncommitted modifications.
  - Interactive file selection with live WSS file content loading and Code Diff Viewer.
- **RAG Tab**: Perform semantic vector code search across indexed project chunks with relevance score metrics.
- **GIT Tab**: Inspect local Git isolation branch (`agent/{instruction_id}`), modified files, untracked files, and trigger branch rollbacks.

---

## 🛠️ Developer Shortcuts

Common shortcuts available via `Makefile`:

```bash
make up          # Start Docker Compose infrastructure
make down        # Stop Docker Compose infrastructure
make dev-api     # Run FastAPI backend locally
make dev-agent   # Run Local Agent daemon
make dev-web     # Run Next.js frontend
make test        # Run API and Local Agent pytest test suites
make lint        # Run linters across Python and TypeScript
```
