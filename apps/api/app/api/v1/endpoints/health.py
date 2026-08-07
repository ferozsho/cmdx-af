"""Health check endpoint."""

import asyncio
from typing import Any

import asyncpg
import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    app_name: str
    environment: str
    mode: str
    version: str


class ComponentHealth(BaseModel):
    """Individual component health status."""

    status: str
    message: str = ""


class FullHealthResponse(BaseModel):
    """Comprehensive infrastructure health check."""

    status: str
    app_name: str
    environment: str
    mode: str
    version: str
    components: dict[str, ComponentHealth]


async def _check_postgres() -> ComponentHealth:
    """Check PostgreSQL connectivity."""
    try:
        conn = await asyncpg.connect(
            settings.DATABASE_URL.replace("+asyncpg", ""),
            timeout=5,
        )
        await conn.execute("SELECT 1")
        await conn.close()
        return ComponentHealth(status="healthy", message="Connected")
    except Exception as e:
        return ComponentHealth(status="unhealthy", message=str(e)[:200])


async def _check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        return ComponentHealth(status="healthy", message="Connected")
    except Exception as e:
        return ComponentHealth(status="unhealthy", message=str(e)[:200])


async def _check_qdrant() -> ComponentHealth:
    """Check Qdrant connectivity."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/collections",
            )
            if resp.status_code == 200:
                return ComponentHealth(status="healthy", message="Connected")
            return ComponentHealth(
                status="degraded",
                message=f"HTTP {resp.status_code}",
            )
    except Exception as e:
        return ComponentHealth(status="unhealthy", message=str(e)[:200])


async def _check_llm() -> ComponentHealth:
    """Check LLM provider connectivity."""
    if not settings.DEEPSEEK_API_KEY:
        return ComponentHealth(status="not_configured", message="No API key set")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.DEEPSEEK_BASE_URL}/models",
                headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            )
            if resp.status_code in (200, 401):
                # 401 means endpoint exists but key may be wrong — still reachable
                return ComponentHealth(status="healthy", message="API reachable")
            return ComponentHealth(
                status="degraded",
                message=f"HTTP {resp.status_code}",
            )
    except Exception as e:
        return ComponentHealth(status="unhealthy", message=str(e)[:200])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Any:
    """Return application health and metadata status."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        mode=settings.APP_MODE,
        version="0.1.0",
    )


@router.get("/health/full", response_model=FullHealthResponse)
async def full_health_check() -> Any:
    """Return comprehensive infrastructure health check."""
    pg_health, redis_health, qdrant_health, llm_health = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_qdrant(),
        _check_llm(),
    )

    components = {
        "postgresql": pg_health,
        "redis": redis_health,
        "qdrant": qdrant_health,
        "deepseek_api": llm_health,
    }

    all_healthy = all(
        c.status == "healthy"
        for c in components.values()
    )

    return FullHealthResponse(
        status="ok" if all_healthy else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        mode=settings.APP_MODE,
        version="0.1.0",
        components=components,
    )
