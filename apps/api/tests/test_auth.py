"""Unit tests for auth: password hashing, JWT, and endpoint guards."""

import asyncio

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_device_token,
    hash_password,
    verify_device_token,
    verify_password,
)
from app.llm.mock import MockLLMProvider
from app.llm.router import LLMConfigurationError, ModelRouter
from app.main import app


@pytest_asyncio.fixture
async def api_client():
    """ASGI-native client compatible with the installed FastAPI release."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


def test_password_hash_roundtrip() -> None:
    """Hashed password verifies; wrong password rejected."""
    hashed = hash_password("SuperSecret123!")
    assert hashed != "SuperSecret123!"
    assert verify_password("SuperSecret123!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hash_is_randomized() -> None:
    """Same password hashes differently each time (bcrypt salt)."""
    assert hash_password("same-pass") != hash_password("same-pass")


def test_jwt_roundtrip() -> None:
    """create_access_token → decode_access_token returns (subject, version)."""
    token = create_access_token("user-123", token_version=2, expires_minutes=30)
    assert decode_access_token(token) == ("user-123", 2)


def test_jwt_rejects_garbage() -> None:
    """Invalid or empty tokens decode to None."""
    assert decode_access_token("not.a.jwt") is None
    assert decode_access_token("") is None


def test_get_current_user_missing_credentials() -> None:
    """No bearer credentials → 401 before touching the DB."""
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(credentials=None, db=None))
    assert exc.value.status_code == 401


def test_get_current_user_invalid_token() -> None:
    """Malformed bearer token → 401."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="garbage.token.value"
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(credentials=creds, db=None))
    assert exc.value.status_code == 401


def test_device_token_hash_roundtrip() -> None:
    """Device credentials are stored as hashes and compared safely."""
    token_hash = hash_device_token("dtk_example")
    assert token_hash != "dtk_example"
    assert verify_device_token("dtk_example", token_hash)
    assert not verify_device_token("dtk_wrong", token_hash)
    assert not verify_device_token("", token_hash)


def test_production_llm_provider_fails_without_key(monkeypatch) -> None:
    """Production never presents a mock response as real provider output."""
    monkeypatch.setattr(settings, "APP_MODE", "production")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "")
    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_KEY"):
        ModelRouter.get_provider("deepseek-chat")


def test_mock_llm_requires_explicit_mode(monkeypatch) -> None:
    """Mock output remains available only when explicitly configured."""
    monkeypatch.setattr(settings, "APP_MODE", "mock")
    provider = ModelRouter.get_provider("deepseek-chat")
    assert isinstance(provider.inner, MockLLMProvider)


@pytest.mark.asyncio
async def test_projects_requires_auth(api_client) -> None:
    """GET /projects without a token → 401 (not mock data)."""
    assert (await api_client.get("/api/v1/projects")).status_code == 401


@pytest.mark.asyncio
async def test_devices_requires_auth(api_client) -> None:
    """GET /devices without a token → 401."""
    assert (await api_client.get("/api/v1/devices")).status_code == 401


@pytest.mark.asyncio
async def test_pairing_code_requires_auth(api_client) -> None:
    """POST /devices/pairing-code without a token → 401."""
    resp = await api_client.post("/api/v1/devices/pairing-code")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_agent_templates_require_auth(api_client) -> None:
    """Agent definitions and their system prompts are not public."""
    assert (await api_client.get("/api/v1/agents")).status_code == 401


@pytest.mark.asyncio
async def test_model_catalog_requires_auth(api_client) -> None:
    """The configured model catalog is available only after sign-in."""
    assert (await api_client.get("/api/v1/settings/models")).status_code == 401


@pytest.mark.asyncio
async def test_project_event_stream_requires_auth(api_client) -> None:
    """Project execution events cannot be observed anonymously."""
    assert (
        await api_client.get("/api/v1/projects/x/stream")
    ).status_code == 401


@pytest.mark.asyncio
async def test_health_stays_public(api_client) -> None:
    """Health endpoint remains unauthenticated."""
    assert (await api_client.get("/api/v1/health")).status_code == 200


@pytest.mark.asyncio
async def test_detailed_health_requires_admin(api_client) -> None:
    """Infrastructure details are not exposed by the public health probe."""
    assert (await api_client.get("/api/v1/health/full")).status_code == 401


@pytest.mark.asyncio
async def test_register_short_password_rejected(api_client) -> None:
    """Password shorter than 6 chars → 422 validation error."""
    resp = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "splash-auth-short@mailinator.com",
            "password": "123",
        },
    )
    assert resp.status_code == 422
