"""Redis-backed fixed-window protection for credential-sensitive endpoints."""

import hashlib
import logging

import redis.asyncio as aioredis
from fastapi import HTTPException

from app.core.config import settings

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
