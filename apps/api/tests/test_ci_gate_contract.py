"""Tests for the external CI verification gate contract (G3)."""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.instruction import Instruction
from app.models.verification_run import VerificationRun
from app.services.verification import evaluate_gate


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
        "/api/v1/auth/register",
        json={
            "email": f"gate-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "Gate Test",
        },
    )
    assert registered.status_code == 201, registered.text
    auth = registered.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    created = await api_client.post(
        "/api/v1/projects", headers=headers, json={"name": f"Gate {suffix}"}
    )
    assert created.status_code == 200, created.text
    return headers, created.json()["id"], auth["user"]["id"]


async def _delete_project(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> None:
    response = await api_client.delete(
        f"/api/v1/projects/{project_id}", headers=headers
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
                prompt="CI gate test",
                status="COMPLETED",
            )
        )
        await session.commit()


async def _insert_run(
    project_id: str,
    instruction_id: str,
    *,
    status: str = "PASSED",
    output_digest: str = "abc123",
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            VerificationRun(
                project_id=project_id,
                instruction_id=instruction_id,
                category="tests",
                executable="pytest",
                command_digest="cmd-digest",
                status=status,
                exit_code=0 if status == "PASSED" else 1,
                output_digest=output_digest,
                output_excerpt="sample evidence",
            )
        )
        await session.commit()


# ── evaluate_gate unit tests ───────────────────────────────────────────────


def test_gate_no_evidence() -> None:
    assert evaluate_gate(stored_status=None, stored_output_digest=None) == (
        "NO_EVIDENCE"
    )
    assert evaluate_gate(stored_status="PASSED", stored_output_digest=None) == (
        "NO_EVIDENCE"
    )


def test_gate_failed_stored_run() -> None:
    assert evaluate_gate(
        stored_status="FAILED", stored_output_digest="d"
    ) == "FAILED"


def test_gate_passed_without_local_digest() -> None:
    assert evaluate_gate(
        stored_status="PASSED", stored_output_digest="d"
    ) == "PASSED"


def test_gate_passed_with_matching_digest() -> None:
    assert evaluate_gate(
        stored_status="PASSED",
        stored_output_digest="d",
        local_output_digest="d",
    ) == "PASSED"


def test_gate_failed_on_digest_mismatch() -> None:
    assert evaluate_gate(
        stored_status="PASSED",
        stored_output_digest="stored",
        local_output_digest="tampered",
    ) == "FAILED"


# ── endpoint contract tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_latest_requires_auth(api_client) -> None:
    response = await api_client.get("/api/v1/projects/x/verification/latest")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_latest_no_evidence(api_client) -> None:
    headers, project_id, _ = await _register_project(api_client)
    try:
        response = await api_client.get(
            f"/api/v1/projects/{project_id}/verification/latest",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["gate_status"] == "NO_EVIDENCE"
        assert body["latest"] is None
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_latest_passed_with_evidence(api_client) -> None:
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    try:
        await _insert_instruction(project_id, user_id, instruction_id)
        await _insert_run(project_id, instruction_id)
        response = await api_client.get(
            f"/api/v1/projects/{project_id}/verification/latest",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["gate_status"] == "PASSED"
        assert body["latest"]["status"] == "PASSED"
        assert body["latest"]["output_digest"] == "abc123"
        assert body["latest"]["category"] == "tests"
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_latest_digest_mismatch_fails(api_client) -> None:
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    try:
        await _insert_instruction(project_id, user_id, instruction_id)
        await _insert_run(project_id, instruction_id, output_digest="stored")
        response = await api_client.get(
            f"/api/v1/projects/{project_id}/verification/latest",
            params={"local_output_digest": "tampered"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["gate_status"] == "FAILED"
    finally:
        await _delete_project(api_client, headers, project_id)


@pytest.mark.asyncio
async def test_latest_foreign_project_is_404(api_client) -> None:
    headers_a, project_id, _ = await _register_project(api_client)
    headers_b, _, _ = await _register_project(api_client)
    try:
        response = await api_client.get(
            f"/api/v1/projects/{project_id}/verification/latest",
            headers=headers_b,
        )
        assert response.status_code == 404
    finally:
        await _delete_project(api_client, headers_a, project_id)
