.PHONY: help up down restart logs dev-api dev-agent dev-web test lint

help:
	@echo "AgentForge Commands:"
	@echo "  make up          Start Docker Compose infrastructure"
	@echo "  make down        Stop Docker Compose infrastructure"
	@echo "  make logs        Tail Docker Compose logs"
	@echo "  make dev-api     Run FastAPI backend locally"
	@echo "  make dev-agent   Run Local Agent daemon"
	@echo "  make dev-web     Run Next.js frontend"
	@echo "  make test        Run all test suites"
	@echo "  make lint        Run linters across Python and TypeScript"

up:
	docker compose -f infrastructure/docker-compose.yml up -d

down:
	docker compose -f infrastructure/docker-compose.yml down

logs:
	docker compose -f infrastructure/docker-compose.yml logs -f

dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

dev-agent:
	cd apps/local-agent && python -m agentforge_local start

dev-web:
	cd apps/web && npm run dev

test:
	cd apps/api && pytest
	cd apps/local-agent && pytest

lint:
	cd apps/api && ruff check .
	cd apps/local-agent && ruff check .
