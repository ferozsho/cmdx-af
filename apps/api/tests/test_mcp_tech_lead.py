"""Integration tests for IDE/MCP and technical-lead project context."""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _register_project(
    api_client: httpx.AsyncClient,
) -> tuple[dict[str, str], str]:
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"mcp-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "MCP Test",
        },
    )
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    project = await api_client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": f"MCP Project {suffix}"},
    )
    return headers, project.json()["id"]


async def test_mcp_requires_auth_and_rejects_untrusted_origin(api_client) -> None:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25"},
    }
    assert (await api_client.post("/mcp", json=body)).status_code == 401
    headers, project_id = await _register_project(api_client)
    try:
        response = await api_client.post(
            "/mcp",
            headers={**headers, "Origin": "https://untrusted.example"},
            json=body,
        )
        assert response.status_code == 403
    finally:
        await api_client.delete(
            f"/api/v1/projects/{project_id}", headers=headers
        )


async def test_mcp_context_tasks_and_instruction_queue(api_client) -> None:
    headers, project_id = await _register_project(api_client)
    try:
        initialized = await api_client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"},
                },
            },
        )
        assert initialized.status_code == 200, initialized.text
        assert initialized.json()["result"]["protocolVersion"] == "2025-11-25"
        session_id = initialized.headers["mcp-session-id"]
        mcp_headers = {
            **headers,
            "Mcp-Session-Id": session_id,
            "MCP-Protocol-Version": "2025-11-25",
        }

        tools = await api_client.post(
            "/mcp",
            headers=mcp_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert tools.status_code == 200, tools.text
        assert len(tools.json()["result"]["tools"]) == 3

        queued = await api_client.post(
            "/mcp",
            headers=mcp_headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "agentforge_submit_instruction",
                    "arguments": {
                        "project_id": project_id,
                        "prompt": "Inspect the current architecture",
                    },
                },
            },
        )
        assert queued.status_code == 200, queued.text
        result = queued.json()["result"]["structuredContent"]
        assert result["status"] == "PENDING"

        tasks = await api_client.get(
            f"/api/v1/projects/{project_id}/tasks", headers=headers
        )
        context = await api_client.get(
            f"/api/v1/projects/{project_id}/context", headers=headers
        )
        assert tasks.status_code == 200, tasks.text
        assert tasks.json()["tasks"][0]["id"] == result["instruction_id"]
        assert context.status_code == 200, context.text
        assert context.json()["project"]["id"] == project_id
    finally:
        await api_client.delete(
            f"/api/v1/projects/{project_id}", headers=headers
        )
