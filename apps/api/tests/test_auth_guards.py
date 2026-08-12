"""Endpoint tests for auth guards, RBAC, and offline degradation.

These integration tests use an ASGI-native HTTP client and a reachable test
PostgreSQL database. Tool-backed endpoints must degrade to a structured
offline response when no paired workstation is connected.
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.core.config import settings
from app.main import app

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


async def _register_user(
    api_client: httpx.AsyncClient,
    email: str | None = None,
    password: str = "User@323123",
    full_name: str = "Test User",
):
    email = email or f"splash-auth-{uuid.uuid4().hex[:10]}@mailinator.com"
    response = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return data["access_token"], data["user"], email, password


# ── 401 guards (no token) ──────────────────────────────────────────────────
async def test_rag_search_requires_auth(api_client) -> None:
    response = await api_client.post(
        "/api/v1/projects/x/rag/search",
        json={"query": "q", "top_k": 5},
    )
    assert response.status_code == 401


async def test_rag_stats_requires_auth(api_client) -> None:
    assert (
        await api_client.get("/api/v1/projects/x/rag/stats")
    ).status_code == 401


async def test_rag_reindex_requires_auth(api_client) -> None:
    assert (
        await api_client.post("/api/v1/projects/x/rag/reindex")
    ).status_code == 401


async def test_validate_path_requires_auth(api_client) -> None:
    response = await api_client.post(
        "/api/v1/projects/validate-path",
        json={"path": "/tmp"},
    )
    assert response.status_code == 401


async def test_git_rollback_requires_auth(api_client) -> None:
    response = await api_client.post(
        "/api/v1/projects/x/git/rollback",
        json={"commit_hash": "abc123"},
    )
    assert response.status_code == 401


async def test_artifacts_requires_auth(api_client) -> None:
    assert (
        await api_client.get("/api/v1/projects/x/artifacts")
    ).status_code == 401


async def test_runs_requires_auth(api_client) -> None:
    assert (
        await api_client.get("/api/v1/projects/x/runs")
    ).status_code == 401


async def test_settings_requires_auth(api_client) -> None:
    assert (await api_client.get("/api/v1/settings")).status_code == 401


async def test_observability_requires_auth(api_client) -> None:
    assert (
        await api_client.get("/api/v1/observability/agent-metrics")
    ).status_code == 401


async def test_list_instructions_requires_auth(api_client) -> None:
    assert (
        await api_client.get("/api/v1/projects/x/instructions")
    ).status_code == 401


async def test_submit_instruction_requires_auth(api_client) -> None:
    response = await api_client.post(
        "/api/v1/projects/x/instructions",
        json={"prompt": "do something"},
    )
    assert response.status_code == 401


# ── RBAC ───────────────────────────────────────────────────────────────────
async def test_settings_forbidden_for_user_role(api_client) -> None:
    """A freshly registered user cannot read administrator settings."""
    token, _, _, _ = await _register_user(api_client)
    response = await api_client.get(
        "/api/v1/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_agent_mutation_forbidden_for_user_role(api_client) -> None:
    """Only administrators may create global agent templates."""
    token, _, _, _ = await _register_user(api_client)
    response = await api_client.post(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Unauthorized Agent"},
    )
    assert response.status_code == 403


# ── Offline degradation (no device connected in test env) ─────────────────
async def test_rag_search_returns_offline_not_500(api_client) -> None:
    """Tool-backed endpoint returns structured offline payload (HTTP 200)."""
    token, _, _, _ = await _register_user(api_client)
    headers = {"Authorization": f"Bearer {token}"}
    project = await api_client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "smoke-test-proj"},
    )
    assert project.status_code == 200, project.text
    project_id = project.json()["id"]
    try:
        response = await api_client.post(
            f"/api/v1/projects/{project_id}/rag/search",
            headers=headers,
            json={"query": "hello", "top_k": 5},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data.get("status") == "offline"
        assert data.get("online") is False
    finally:
        await api_client.delete(
            f"/api/v1/projects/{project_id}",
            headers=headers,
        )


async def test_cross_user_project_access_is_denied(api_client) -> None:
    """Project-scoped tool and session APIs reject a different user."""
    owner_token, _, _, _ = await _register_user(api_client)
    intruder_token, _, _, _ = await _register_user(api_client)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    intruder_headers = {"Authorization": f"Bearer {intruder_token}"}
    project = await api_client.post(
        "/api/v1/projects",
        headers=owner_headers,
        json={"name": "ownership-test-proj"},
    )
    assert project.status_code == 200, project.text
    project_id = project.json()["id"]

    try:
        responses = [
            await api_client.get(
                f"/api/v1/projects/{project_id}/tree",
                headers=intruder_headers,
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/files/content",
                headers=intruder_headers,
                params={"path": "README.md"},
            ),
            await api_client.post(
                f"/api/v1/projects/{project_id}/rag/search",
                headers=intruder_headers,
                json={"query": "secrets", "top_k": 5},
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/rag/chunks",
                headers=intruder_headers,
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/rag/stats",
                headers=intruder_headers,
            ),
            await api_client.post(
                f"/api/v1/projects/{project_id}/rag/reindex",
                headers=intruder_headers,
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/rag/reindex-status",
                headers=intruder_headers,
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/git/status",
                headers=intruder_headers,
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/git/log",
                headers=intruder_headers,
            ),
            await api_client.post(
                f"/api/v1/projects/{project_id}/git/rollback",
                headers=intruder_headers,
                json={"commit_hash": "abc123"},
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/files/original",
                headers=intruder_headers,
                params={"path": "README.md"},
            ),
            await api_client.get(
                f"/api/v1/projects/{project_id}/sessions",
                headers=intruder_headers,
            ),
            await api_client.post(
                f"/api/v1/projects/{project_id}/sessions",
                headers=intruder_headers,
                json={"name": "stolen session"},
            ),
        ]
        assert all(response.status_code == 404 for response in responses), [
            (response.status_code, response.text) for response in responses
        ]
    finally:
        await api_client.delete(
            f"/api/v1/projects/{project_id}",
            headers=owner_headers,
        )


# ── Refresh token rotation ─────────────────────────────────────────────────
async def test_login_returns_refresh_token(api_client) -> None:
    """Login returns both an access and a refresh token."""
    _, _, email, password = await _register_user(api_client)
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


async def test_refresh_rotates_and_revokes_old(api_client) -> None:
    """A refresh token is single-use: rotation revokes the old one."""
    _, _, email, password = await _register_user(api_client)
    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    refresh_token = login_response.json()["refresh_token"]

    rotated = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert rotated.status_code == 200, rotated.text
    new_refresh_token = rotated.json()["refresh_token"]
    assert new_refresh_token and new_refresh_token != refresh_token

    reused = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused.status_code == 401


async def test_logout_revokes_refresh_token(api_client) -> None:
    """Server-side logout revokes the refresh token."""
    _, _, email, password = await _register_user(api_client)
    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    refresh_token = login_response.json()["refresh_token"]

    logged_out = await api_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logged_out.status_code == 200

    reused = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused.status_code == 401


# ── Forgot / reset password ────────────────────────────────────────────────
async def test_forgot_and_reset_password_flow(api_client, monkeypatch) -> None:
    """Production hides reset tokens; explicit mock mode supports local tests."""
    old_password = "User@323122"
    _, _, email, _ = await _register_user(api_client, password=old_password)

    monkeypatch.setattr(settings, "APP_MODE", "production")
    forgot = await api_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert forgot.status_code == 200, forgot.text
    assert "reset_token" not in forgot.json()

    monkeypatch.setattr(settings, "APP_MODE", "mock")
    forgot = await api_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert forgot.status_code == 200, forgot.text
    token = forgot.json().get("reset_token")
    assert token

    new_password = "User@323123"
    reset = await api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset.status_code == 200, reset.text

    old_login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login.status_code == 401

    new_login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login.status_code == 200
