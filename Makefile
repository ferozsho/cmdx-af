.PHONY: help up down restart logs up-agent down-agent logs-agent dev-api dev-agent dev-web test typecheck build verify lint

help:
	@echo "AgentForge Commands:"
	@echo "  make up           Start Docker Compose infrastructure"
	@echo "  make down         Stop Docker Compose infrastructure"
	@echo "  make logs         Tail Docker Compose logs"
	@echo "  make up-agent     Start the local agent in Docker (set AGENT_WORKSPACE=path)"
	@echo "  make down-agent   Stop the local agent container"
	@echo "  make logs-agent   Tail local agent logs"
	@echo "  make dev-api      Run FastAPI backend locally"
	@echo "  make dev-agent    Run Local Agent daemon natively"
	@echo "  make dev-web      Run Next.js frontend"
	@echo "  make test         Run all test suites"
	@echo "  make typecheck    Type-check the web application"
	@echo "  make build        Build the production web application"
	@echo "  make verify       Run tests, type-check, and production build"
	@echo "  make lint         Run linters across Python and TypeScript"

up:
	docker compose --env-file .env -f infrastructure/docker-compose.yml up -d

down:
	docker compose --env-file .env -f infrastructure/docker-compose.yml down

logs:
	docker compose --env-file .env -f infrastructure/docker-compose.yml logs -f

up-agent:
	docker compose --env-file .env -f infrastructure/docker-compose.local-agent.yml up -d --build

down-agent:
	docker compose --env-file .env -f infrastructure/docker-compose.local-agent.yml down

logs-agent:
	docker compose --env-file .env -f infrastructure/docker-compose.local-agent.yml logs -f

dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

dev-agent:
	cd apps/local-agent && python -m agentforge_local start

dev-web:
	cd apps/web && npm run dev

test:
	cd apps/api && ../../.venv/bin/python -m pytest
	cd apps/local-agent && ../../.venv/bin/python -m pytest

typecheck:
	cd apps/web && ./node_modules/.bin/tsc --noEmit

build:
	cd apps/web && npm run build

verify: test typecheck build

lint:
	cd apps/api && ../../.venv/bin/ruff check --config pyproject.toml .
	cd apps/local-agent && ../../.venv/bin/ruff check --config pyproject.toml .
	cd apps/web && npm run lint
