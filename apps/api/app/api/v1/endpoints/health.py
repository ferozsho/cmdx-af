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


async def _check_llm(provider: str) -> ComponentHealth:
    """Check an LLM provider connectivity."""
    from app.core.config import get_setting

    configs = {
        "deepseek": {
            "key_setting": "DEEPSEEK_API_KEY",
            "url_setting": "DEEPSEEK_BASE_URL",
            "default_url": "https://api.deepseek.com/v1",
            "label": "DeepSeek API",
        },
        "openai": {
            "key_setting": "OPENAI_API_KEY",
            "url_setting": "OPENAI_BASE_URL",
            "default_url": "https://api.openai.com/v1",
            "label": "OpenAI API",
        },
        "claude": {
            "key_setting": "CLAUDE_API_KEY",
            "url_setting": None,
            "default_url": "https://api.anthropic.com/v1/messages",
            "label": "Claude API",
            "health_method": "post",
        },
        "gemini": {
            "key_setting": "GEMINI_API_KEY",
            "url_setting": None,
            "default_url": "https://generativelanguage.googleapis.com/v1beta",
            "label": "Gemini API",
        },
    }

    cfg = configs.get(provider)
    if not cfg:
        return ComponentHealth(status="unknown", message="Unknown provider")

    api_key = get_setting(cfg["key_setting"], "")
    if not api_key:
        return ComponentHealth(
            status="not_configured", message="No API key set"
        )

    base_url = (
        get_setting(cfg["url_setting"], cfg["default_url"])
        if cfg["url_setting"]
        else cfg["default_url"]
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            method = cfg.get("health_method", "get")
            if method == "post":
                resp = await client.post(
                    base_url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                if resp.status_code in (200, 400, 401):
                    return ComponentHealth(
                        status="healthy", message="API reachable"
                    )
            else:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code in (200, 401):
                    return ComponentHealth(
                        status="healthy", message="API reachable"
                    )
            return ComponentHealth(
                status="degraded", message=f"HTTP {resp.status_code}",
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
    pg_health, redis_health, qdrant_health, ds, oa, cl, gm = (
        await asyncio.gather(
            _check_postgres(),
            _check_redis(),
            _check_qdrant(),
            _check_llm("deepseek"),
            _check_llm("openai"),
            _check_llm("claude"),
            _check_llm("gemini"),
        )
    )

    components = {
        "postgresql": pg_health,
        "redis": redis_health,
        "qdrant": qdrant_health,
        "deepseek_api": ds,
        "openai_api": oa,
        "claude_api": cl,
        "gemini_api": gm,
    }

    statuses = [c.status for c in components.values()]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        # healthy + not_configured (e.g. no DeepSeek key yet) is NOT a degradation
        overall = "ok"

    return FullHealthResponse(
        status=overall,
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        mode=settings.APP_MODE,
        version="0.1.0",
        components=components,
    )
