"""Endpoint tests: auth guards, RBAC, and offline degradation.

These tests need a reachable Postgres (used for register + project create).
The device is offline in the test env, so tool-backed endpoints must return
the structured ``{status: "offline", online: false}`` payload (HTTP 200)
instead of a 500.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_user(
    email: str | None = None,
    password: str = "testpass123",
    full_name: str = "Test User",
):
    email = email or f"t{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    return data["access_token"], data["user"], email, password


# ── 401 guards (no token) ──────────────────────────────────────────────────
def test_rag_search_requires_auth() -> None:
    assert (
        client.post(
            "/api/v1/projects/x/rag/search",
            json={"query": "q", "top_k": 5},
        ).status_code
        == 401
    )


def test_rag_stats_requires_auth() -> None:
    assert client.get("/api/v1/projects/x/rag/stats").status_code == 401


def test_rag_reindex_requires_auth() -> None:
    assert client.post("/api/v1/projects/x/rag/reindex").status_code == 401


def test_validate_path_requires_auth() -> None:
    assert (
        client.post(
            "/api/v1/projects/validate-path", json={"path": "/tmp"}
        ).status_code
        == 401
    )


def test_git_rollback_requires_auth() -> None:
    assert (
        client.post(
            "/api/v1/projects/x/git/rollback",
            json={"commit_hash": "abc123"},
        ).status_code
        == 401
    )


def test_artifacts_requires_auth() -> None:
    assert client.get("/api/v1/projects/x/artifacts").status_code == 401


def test_runs_requires_auth() -> None:
    assert client.get("/api/v1/projects/x/runs").status_code == 401


def test_settings_requires_auth() -> None:
    assert client.get("/api/v1/settings").status_code == 401


def test_observability_requires_auth() -> None:
    assert client.get("/api/v1/observability/agent-metrics").status_code == 401


def test_list_instructions_requires_auth() -> None:
    assert client.get("/api/v1/projects/x/instructions").status_code == 401


def test_submit_instruction_requires_auth() -> None:
    assert (
        client.post(
            "/api/v1/projects/x/instructions",
            json={"prompt": "do something"},
        ).status_code
        == 401
    )


# ── RBAC ───────────────────────────────────────────────────────────────────
def test_settings_forbidden_for_user_role() -> None:
    """A freshly registered (role=user) account cannot read settings."""
    token, _, _, _ = _register_user()
    res = client.get(
        "/api/v1/settings", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


# ── Offline degradation (no device connected in test env) ─────────────────
def test_rag_search_returns_offline_not_500() -> None:
    """Tool-backed endpoint returns structured offline payload (HTTP 200)."""
    token, _, _, _ = _register_user()
    proj = client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "smoke-test-proj"},
    )
    assert proj.status_code == 200, proj.text
    pid = proj.json()["id"]
    try:
        res = client.post(
            f"/api/v1/projects/{pid}/rag/search",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "hello", "top_k": 5},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data.get("status") == "offline"
        assert data.get("online") is False
    finally:
        client.delete(
            f"/api/v1/projects/{pid}",
            headers={"Authorization": f"Bearer {token}"},
        )
