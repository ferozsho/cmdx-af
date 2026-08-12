"""Endpoint tests for DB-backed API key management (PUT /settings/keys).

These integration tests use an ASGI-native HTTP client and a reachable test
PostgreSQL database (same setup as test_auth_guards.py). The test DB must be
migrated (``alembic upgrade head``) so the ``platform_settings`` table exists.
"""

import uuid

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.config import db_secret_settings, settings
from app.core.database import AsyncSessionLocal
from app.core.secrets import decrypt_secret
from app.main import app
from app.models.platform_setting import PlatformSetting
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api_client():
    """ASGI-native client compatible with the installed FastAPI release."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def _register_admin(api_client: httpx.AsyncClient) -> str:
    """Register a user and promote them to admin directly in the DB."""
    email = f"keys-admin-{uuid.uuid4().hex[:10]}@mailinator.com"
    response = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Admin@323123",
            "full_name": "Keys Admin",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.role = "admin"
        await db.commit()
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_keys_requires_auth(api_client) -> None:
    response = await api_client.put(
        "/api/v1/settings/keys",
        json={"provider": "deepseek", "api_key": "sk-test-1234567890"},
    )
    assert response.status_code == 401


async def test_keys_forbidden_for_user_role(api_client) -> None:
    email = f"keys-user-{uuid.uuid4().hex[:10]}@mailinator.com"
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "User@323123", "full_name": "U"},
    )
    token = response.json()["access_token"]
    response = await api_client.put(
        "/api/v1/settings/keys",
        headers=_headers(token),
        json={"provider": "deepseek", "api_key": "sk-test-1234567890"},
    )
    assert response.status_code == 403


async def test_unknown_provider_returns_404(api_client) -> None:
    token = await _register_admin(api_client)
    response = await api_client.put(
        "/api/v1/settings/keys",
        headers=_headers(token),
        json={"provider": "nope", "api_key": "sk-test-1234567890"},
    )
    assert response.status_code == 404


async def test_empty_and_short_keys_rejected(api_client) -> None:
    token = await _register_admin(api_client)
    headers = _headers(token)

    empty = await api_client.put(
        "/api/v1/settings/keys",
        headers=headers,
        json={"provider": "deepseek", "api_key": "   "},
    )
    assert empty.status_code == 400

    short = await api_client.put(
        "/api/v1/settings/keys",
        headers=headers,
        json={"provider": "deepseek", "api_key": "abc"},
    )
    assert short.status_code == 400


async def test_set_replace_and_remove_key(api_client) -> None:
    token = await _register_admin(api_client)
    headers = _headers(token)

    # Store a key: encrypted at rest, decrypted into the in-memory cache, and
    # reported as configured by GET /settings.
    response = await api_client.put(
        "/api/v1/settings/keys",
        headers=headers,
        json={"provider": "deepseek", "api_key": "sk-db-test-abcdefgh"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    assert db_secret_settings.get("DEEPSEEK_API_KEY") == "sk-db-test-abcdefgh"

    settings_response = await api_client.get(
        "/api/v1/settings", headers=headers
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["has_deepseek_key"] is True

    # Encrypted at rest — raw plaintext must never be persisted.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PlatformSetting).where(
                PlatformSetting.key == "DEEPSEEK_API_KEY"
            )
        )
        row = result.scalar_one()
        assert row.is_secret is True
        assert row.value != "sk-db-test-abcdefgh"
        assert decrypt_secret(row.value) == "sk-db-test-abcdefgh"

    # Replace.
    response = await api_client.put(
        "/api/v1/settings/keys",
        headers=headers,
        json={"provider": "deepseek", "api_key": "sk-db-test-newkey123"},
    )
    assert response.status_code == 200
    assert db_secret_settings.get("DEEPSEEK_API_KEY") == "sk-db-test-newkey123"

    # Remove.
    response = await api_client.put(
        "/api/v1/settings/keys",
        headers=headers,
        json={"provider": "deepseek", "api_key": "__remove__"},
    )
    assert response.status_code == 200
    assert "DEEPSEEK_API_KEY" not in db_secret_settings

    settings_response = await api_client.get(
        "/api/v1/settings", headers=headers
    )
    assert settings_response.json()["has_deepseek_key"] is (
        bool(settings.DEEPSEEK_API_KEY)
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PlatformSetting).where(
                PlatformSetting.key == "DEEPSEEK_API_KEY"
            )
        )
        assert result.scalar_one_or_none() is None
