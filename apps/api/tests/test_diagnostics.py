"""Tests for runtime diagnostics capture as verification evidence (G7b)."""

import uuid
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio

import app.api.v1.endpoints.projects as projects_mod
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.instruction import Instruction

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
) -> tuple[dict[str, str], str, str]:
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        f"{BASE}/auth/register",
        json={
            "email": f"diag-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "Diagnostics Test",
        },
    )
    assert registered.status_code == 201, registered.text
    auth = registered.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    created = await api_client.post(
        f"{BASE}/projects", headers=headers, json={"name": f"Diag {suffix}"}
    )
    assert created.status_code == 200, created.text
    return headers, created.json()["id"], auth["user"]["id"]


async def _delete_project(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> None:
    response = await api_client.delete(
        f"{BASE}/projects/{project_id}", headers=headers
    )
    assert response.status_code == 200, response.text


async def _insert_instruction(
    project_id: str, user_id: str, instruction_id: str
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            Instruction(
                id=instruction_id,
                project_id=project_id,
                user_id=user_id,
                prompt="Diagnostics test",
                status="COMPLETED",
            )
        )
        await session.commit()


async def _fake_authorize(**kwargs: object) -> str:
    return "policy:test"


async def _fake_invoke_success(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(
        success=True,
        result={
            "tests_passed": 12,
            "tests_failed": 0,
            "summary": "12 passed in 1.2s",
        },
        error=None,
    )


@pytest.mark.asyncio
async def test_diagnostics_requires_auth(api_client) -> None:
    response = await api_client.post(f"{BASE}/projects/x/diagnostics", json={})
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_diagnostics_requires_instruction(api_client) -> None:
    headers, project_id, _ = await _register_project(api_client)
    try:
        response = await api_client.post(
            f"{BASE}/projects/{project_id}/diagnostics",
            headers=headers,
            json={},
        )
        assert response.status_code == 400, response.text
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_diagnostics_records_evidence(api_client, monkeypatch) -> None:
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    recorded: dict = {}

    async def fake_record_verification(**kwargs: object) -> None:
        recorded.update(kwargs)

    try:
        await _insert_instruction(project_id, user_id, instruction_id)
        monkeypatch.setattr(projects_mod, "authorize_tool", _fake_authorize)
        monkeypatch.setattr(
            projects_mod.ToolGateway, "invoke_tool", _fake_invoke_success
        )
        monkeypatch.setattr(
            projects_mod, "record_verification", fake_record_verification
        )

        response = await api_client.post(
            f"{BASE}/projects/{project_id}/diagnostics",
            headers=headers,
            json={},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is True
        assert body["category"] == "diagnostics"
        assert body["instruction_id"] == instruction_id

        assert recorded["category"] == "diagnostics"
        assert recorded["project_id"] == project_id
        assert recorded["instruction_id"] == instruction_id
        assert recorded["command"] == ["pytest", "-q", "--durations=5"]
        assert recorded["result"]["tests_passed"] == 12
        assert "duration_seconds" in recorded["result"]
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_diagnostics_offline(api_client, monkeypatch) -> None:
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"

    async def fake_invoke_offline(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(success=False, result=None, error="Device offline.")

    try:
        await _insert_instruction(project_id, user_id, instruction_id)
        monkeypatch.setattr(projects_mod, "authorize_tool", _fake_authorize)
        monkeypatch.setattr(
            projects_mod.ToolGateway, "invoke_tool", fake_invoke_offline
        )
        response = await api_client.post(
            f"{BASE}/projects/{project_id}/diagnostics",
            headers=headers,
            json={},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "offline"
    finally:
        await _delete_project(api_client, headers, project_id)
