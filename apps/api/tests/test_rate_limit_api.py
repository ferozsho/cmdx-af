"""Tests for API-wide rate limiting (G1)."""

import uuid

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.main import app
from app.services import rate_limit
from app.services.rate_limit import enforce_api_rate_limit

pytestmark = pytest.mark.asyncio


class _FakeRedis:
    """In-memory fixed-window counter mimicking the redis.asyncio client."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, 60)

    async def aclose(self) -> None:
        return None


@pytest_asyncio.fixture
async def api_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def _register(
    api_client: httpx.AsyncClient,
) -> dict[str, str]:
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"rate-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "Rate Limit Test",
        },
    )
    assert registered.status_code == 201, registered.text
    body = registered.json()
    return {"Authorization": f"Bearer {body['access_token']}"}


async def test_raises_structured_429_over_limit(monkeypatch) -> None:
    """The API helper raises a structured 429 after the ceiling is exceeded."""
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit.aioredis, "from_url", lambda url: fake)

    for _ in range(2):
        await enforce_api_rate_limit(
            "api:test", "user-1", limit=2, window_seconds=60
        )
    with pytest.raises(HTTPException) as exc_info:
        await enforce_api_rate_limit(
            "api:test", "user-1", limit=2, window_seconds=60
        )
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == {
        "status": "rate_limited",
        "retry_after_seconds": 60,
    }
    assert exc_info.value.headers["Retry-After"] == "60"


async def test_identities_are_isolated(monkeypatch) -> None:
    """Different identities keep separate counters (per-user / per-IP keys)."""
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit.aioredis, "from_url", lambda url: fake)

    for _ in range(2):
        await enforce_api_rate_limit(
            "api:test", "user-a", limit=2, window_seconds=60
        )
    # user-a exhausts its ceiling on the next call.
    with pytest.raises(HTTPException):
        await enforce_api_rate_limit(
            "api:test", "user-a", limit=2, window_seconds=60
        )
    # A different identity is unaffected and must not raise.
    await enforce_api_rate_limit(
        "api:test", "user-b", limit=2, window_seconds=60
    )


async def test_fails_open_when_redis_unavailable(monkeypatch) -> None:
    """Redis outage must not break mutating endpoints (fail-open)."""

    class _BrokenClient:
        async def incr(self, key: str) -> int:  # noqa: ARG002
            raise ConnectionError("redis down")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(
        rate_limit.aioredis, "from_url", lambda url: _BrokenClient()
    )
    # Must not raise despite the Redis store being unavailable.
    await enforce_api_rate_limit(
        "api:test", "user-1", limit=1, window_seconds=60
    )


async def test_auth_helper_keeps_legacy_string_detail(monkeypatch) -> None:
    """The pre-existing auth helper is untouched (string detail, not dict)."""
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit.aioredis, "from_url", lambda url: fake)

    for _ in range(1):
        await rate_limit.enforce_rate_limit(
            "login", "a@b.c", limit=1, window_seconds=60
        )
    with pytest.raises(HTTPException) as exc_info:
        await rate_limit.enforce_rate_limit(
            "login", "a@b.c", limit=1, window_seconds=60
        )
    assert exc_info.value.status_code == 429
    assert isinstance(exc_info.value.detail, str)


async def test_mutating_endpoint_surfaces_429(api_client, monkeypatch) -> None:
    """A mutating endpoint (POST /projects) enforces the API dependency."""
    headers = await _register(api_client)

    async def _boom(
        scope: str,
        identity: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> None:
        raise HTTPException(
            status_code=429,
            detail={"status": "rate_limited", "retry_after_seconds": 5},
            headers={"Retry-After": "5"},
        )

    monkeypatch.setattr(rate_limit, "enforce_api_rate_limit", _boom)
    response = await api_client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Rate Limited Project"},
    )
    assert response.status_code == 429
    assert response.json() == {
        "status": "rate_limited",
        "retry_after_seconds": 5,
    }


async def test_unauthenticated_mutating_request_rejected(api_client) -> None:
    """Mutating endpoints still require a valid token before anything runs."""
    response = await api_client.post(
        "/api/v1/projects",
        json={"name": "No Auth"},
    )
    assert response.status_code in {401, 403}
