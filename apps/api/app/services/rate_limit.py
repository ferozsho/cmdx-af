"""Redis-backed fixed-window protection for credential-sensitive endpoints."""

import hashlib
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


async def enforce_rate_limit(
    bucket: str,
    identity: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise 429 after a bounded number of attempts; fail open on Redis outage."""
    digest = hashlib.sha256(identity.strip().lower().encode("utf-8")).hexdigest()
    key = f"agentforge:rate:{bucket}:{digest}"
    client = aioredis.from_url(settings.REDIS_URL)
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window_seconds)
        if count > limit:
            ttl = max(1, int(await client.ttl(key)))
            raise HTTPException(
                status_code=429,
                detail="Too many requests; try again later",
                headers={"Retry-After": str(ttl)},
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Rate-limit store unavailable for bucket %s", bucket)
    finally:
        await client.aclose()


async def enforce_api_rate_limit(
    scope: str,
    identity: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise a structured 429 for API-wide ceilings; fail open on Redis outage."""
    digest = hashlib.sha256(identity.strip().lower().encode("utf-8")).hexdigest()
    key = f"agentforge:rate:{scope}:{digest}"
    client = aioredis.from_url(settings.REDIS_URL)
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window_seconds)
        if count > limit:
            ttl = max(1, int(await client.ttl(key)))
            raise HTTPException(
                status_code=429,
                detail={
                    "status": "rate_limited",
                    "retry_after_seconds": ttl,
                },
                headers={"Retry-After": str(ttl)},
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Rate-limit store unavailable for scope %s", scope)
    finally:
        await client.aclose()


def api_rate_limit(scope: str) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency enforcing per-user and per-IP ceilings.

    The returned dependency authenticates the caller (401 on bad tokens),
    then enforces the configured per-user and per-IP budgets for the scope.
    """

    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> None:
        ip = request.client.host if request.client else "unknown"
        await enforce_api_rate_limit(
            f"api:{scope}:user",
            current_user.id,
            limit=settings.RATE_LIMIT_MUTATING_PER_MIN,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        await enforce_api_rate_limit(
            f"api:{scope}:ip",
            ip,
            limit=settings.RATE_LIMIT_IP_PER_MIN,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        )

    return dependency
