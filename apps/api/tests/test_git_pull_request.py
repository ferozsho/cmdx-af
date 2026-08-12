"""Tests for PR creation from agent branches (G7a)."""

import uuid
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio

import app.api.v1.endpoints.projects as projects_mod
from app.main import app
from app.services.approvals import ApprovalRequiredError
from tests.helpers import seed_rag_indexed

BASE = "/api/v1"


@pytest_asyncio.fixture
async def api_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def _register_project(
    api_client: httpx.AsyncClient,
) -> tuple[dict[str, str], str]:
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        f"{BASE}/auth/register",
        json={
            "email": f"pr-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "PR Test",
        },
    )
    assert registered.status_code == 201, registered.text
    auth = registered.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    created = await api_client.post(
        f"{BASE}/projects", headers=headers, json={"name": f"PR {suffix}"}
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]
    await seed_rag_indexed(project_id)
    return headers, project_id


async def _delete_project(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> None:
    response = await api_client.delete(
        f"{BASE}/projects/{project_id}", headers=headers
    )
    assert response.status_code == 200, response.text


def _pr_body(branch: str = "agent/ins_abc") -> dict:
    return {
        "branch_name": branch,
        "title": "Fix the payment module",
        "body": "Fixes #1",
        "base": "main",
    }


@pytest.mark.asyncio
async def test_pull_request_requires_auth(api_client) -> None:
    response = await api_client.post(
        f"{BASE}/projects/x/git/pull-request", json=_pr_body()
    )
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_pull_request_success(api_client, monkeypatch) -> None:
    headers, project_id = await _register_project(api_client)
    try:
        async def fake_authorize_tool(**kwargs: object) -> str:
            return "policy:test"

        async def fake_invoke_tool(**kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                success=True,
                result={"pr_url": "https://github.com/acme/repo/pull/7"},
                error=None,
            )

        monkeypatch.setattr(projects_mod, "authorize_tool", fake_authorize_tool)
        monkeypatch.setattr(
            projects_mod.ToolGateway, "invoke_tool", fake_invoke_tool
        )

        response = await api_client.post(
            f"{BASE}/projects/{project_id}/git/pull-request",
            headers=headers,
            json=_pr_body(),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is True
        assert body["result"]["pr_url"] == (
            "https://github.com/acme/repo/pull/7"
        )
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_pull_request_waits_for_approval(api_client, monkeypatch) -> None:
    headers, project_id = await _register_project(api_client)
    try:
        async def fake_authorize_tool(**kwargs: object) -> str:
            raise ApprovalRequiredError(
                "approval_1", "PR creation needs a human decision"
            )

        monkeypatch.setattr(projects_mod, "authorize_tool", fake_authorize_tool)

        response = await api_client.post(
            f"{BASE}/projects/{project_id}/git/pull-request",
            headers=headers,
            json=_pr_body(),
        )
        assert response.status_code == 202, response.text
        body = response.json()
        assert body["status"] == "WAITING_APPROVAL"
        assert body["approval_id"] == "approval_1"
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_pull_request_offline(api_client, monkeypatch) -> None:
    headers, project_id = await _register_project(api_client)
    try:
        async def fake_authorize_tool(**kwargs: object) -> str:
            return "policy:test"

        async def fake_invoke_tool(**kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                success=False,
                result=None,
                error="Device is offline.",
            )

        monkeypatch.setattr(projects_mod, "authorize_tool", fake_authorize_tool)
        monkeypatch.setattr(
            projects_mod.ToolGateway, "invoke_tool", fake_invoke_tool
        )

        response = await api_client.post(
            f"{BASE}/projects/{project_id}/git/pull-request",
            headers=headers,
            json=_pr_body(),
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "offline"
    finally:
        await _delete_project(api_client, headers, project_id)
