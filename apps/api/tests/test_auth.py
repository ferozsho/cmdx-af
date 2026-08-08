"""Unit tests for auth: password hashing, JWT, and endpoint guards."""

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.main import app

client = TestClient(app)


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
    """create_access_token → decode_access_token returns the subject."""
    token = create_access_token("user-123", expires_minutes=30)
    assert decode_access_token(token) == "user-123"


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


def test_projects_requires_auth() -> None:
    """GET /projects without a token → 401 (not mock data)."""
    assert client.get("/api/v1/projects").status_code == 401


def test_devices_requires_auth() -> None:
    """GET /devices without a token → 401."""
    assert client.get("/api/v1/devices").status_code == 401


def test_pairing_code_requires_auth() -> None:
    """POST /devices/pairing-code without a token → 401."""
    resp = client.post("/api/v1/devices/pairing-code")
    assert resp.status_code == 401


def test_health_stays_public() -> None:
    """Health endpoint remains unauthenticated."""
    assert client.get("/api/v1/health").status_code == 200


def test_register_short_password_rejected() -> None:
    """Password shorter than 6 chars → 422 validation error."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "123"},
    )
    assert resp.status_code == 422
