# AgentForge — AI Agent Framework

AgentForge is an enterprise-grade multi-agent software development platform featuring a Cloud Control Plane and a Local Execution Agent for secure local codebase modifications.

## Architecture Overview

- **Apps**:
  - `apps/web`: Next.js 16+ App Router web control plane.
  - `apps/api`: FastAPI backend orchestrator & Tool Gateway.
  - `apps/local-agent`: Python local execution daemon running on developer workstations.
- **Packages**:
  - `packages/protocol`: Shared message protocol schemas.
- **Infrastructure**:
  - PostgreSQL 16
  - Redis 7
  - Qdrant Vector DB
  - Celery worker

## Quick Start

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Start Cloud infrastructure via Docker Compose:
   ```bash
   docker compose -f infrastructure/docker-compose.yml up -d
   ```

3. Run API backend locally:
   ```bash
   cd apps/api && pip install -e . && uvicorn app.main:app --reload
   ```

4. Run Local Agent daemon:
   ```bash
   cd apps/local-agent && pip install -e . && python -m agentforge_local start
   ```

5. Run Web Frontend:
   ```bash
   cd apps/web && npm install && npm run dev
   ```

## Development Commands

See `Makefile` for convenient developer shortcuts.
