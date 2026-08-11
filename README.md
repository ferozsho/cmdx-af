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

### Quick Start (Makefile)

The fastest way to get everything running:

```bash
# 1. Start all infrastructure (PostgreSQL, Redis, Qdrant, API, Web UI)
make up

# 2. Log in at http://localhost:3000/login
#    Admin: admin@agentforge.ai / Admin@323123

# 3. Start the local agent (mounts your workspace so projects go online)
AGENT_WORKSPACE=/home/administrator/cmdx-af make up-agent

# 4. Verify — dashboard should show ● LOCAL (not offline)
```

To stop everything:

```bash
make down-agent   # Stop local agent
make down         # Stop infrastructure
```

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

3. **Start the Local Execution Agent** — see [💻 Running the Local Agent](#-running-the-local-agent) below
   (native on your PC, or as a separate Docker container).

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

3. **Start Local Agent Daemon** — see [💻 Running the Local Agent](#-running-the-local-agent) below.

4. **Start Next.js Frontend Control Plane**:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

---

## 💻 Running the Local Agent

The Local Execution Daemon (`agentforge_local`) is the piece that runs **on your
workstation** and actually touches files, runs tests, and executes git. It connects
**outbound** to the cloud via WebSocket — no inbound ports or port forwarding needed.

### 1. Pair the workstation (one time)

Generate a pairing code in the UI (**Devices → Generate Pairing Code**), then on
your PC:

```bash
# Native install (if not already done)
pip install -e packages/protocol -e apps/local-agent

# Exchange the code for device credentials (saved to ~/.agentforge/device.json)
agentforge connect AGF-XXXX
```

### 2. Register a project workspace

```bash
# Map a workspace id (the API targets "ws-test" by default) to a local folder
agentforge workspace-add ws-test "D:\Projects\my-app"
agentforge workspace-list
```

### 3. Start the daemon

**Option A — Native (recommended for development):**
```bash
cd apps/local-agent
agentforge start
```
This also starts a file watcher that auto re-indexes RAG on file changes.

**Option B — Docker (no Python setup on the host):**
```bash
# Mount your project folder and start the container (joins the infra network)
AGENT_WORKSPACE="/home/you/projects/my-app" \
  docker compose -f infrastructure/docker-compose.local-agent.yml up -d --build

# Register the mounted folder as the API's default workspace
docker exec agentforge-local agentforge workspace-add ws-test /workspace

# Optional: pair as a real device
docker exec -it agentforge-local agentforge connect AGF-XXXX

# Check logs / stop
docker compose -f infrastructure/docker-compose.local-agent.yml logs -f
docker compose -f infrastructure/docker-compose.local-agent.yml down
```

**Verify it connected:** the Devices page should show the workstation as
**Online (WSS Connected)**, and RAG / Files / Git tabs will use live data. If the
daemon is not running, those tabs degrade gracefully with an "offline" notice.

---

## 💻 Local Agent CLI Commands

```bash
# Pair this workstation with the cloud using a code from the Devices page
agentforge connect AGF-XXXX

# Register an authorized local project workspace path
agentforge workspace-add prj_demo_001 "D:\Projects\my-app"

# List registered local project workspaces
agentforge workspace-list

# Start outbound WSS daemon (+ file watcher for auto RAG re-indexing)
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

## � Commit & Push

All commits must carry the correct `--author` flag based on the IDE AI provider
in use:

```bash
# Stage and commit with author attribution
git add .
git commit --author="Name <email>" -m "Your commit message"

# Push to remote
git push origin <branch_name>
```

**Author convention:** the `--author` value depends on which IDE AI provider
(GitHub Copilot, Cursor, etc.) generated the change. Always verify authorship
before pushing.

---

## �🛠️ Developer Shortcuts

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
