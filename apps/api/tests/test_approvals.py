"""Integration tests for durable policy approvals and pipeline resume."""

import uuid
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.agents.pipeline import PipelineOrchestrator
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.approval import ApprovalRequest
from app.models.instruction import Instruction
from app.models.project import Project
from app.services.approvals import ApprovalRequiredError, authorize_tool
from tests.helpers import seed_rag_indexed

pytestmark = pytest.mark.asyncio


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
            "email": f"approval-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "Approval Test",
        },
    )
    assert registered.status_code == 201, registered.text
    body = registered.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    created = await api_client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": f"Approval Project {suffix}"},
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]
    await seed_rag_indexed(project_id)
    return headers, project_id, body["user"]["id"]


class CommandAgent:
    """Fake agent whose high-risk command requires a project approval."""

    agent_name = "Command Agent"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        project = context["project_config"]
        authorization = await authorize_tool(
            project=project,
            user_id=context["user_id"],
            instruction_id=context["instruction_id"],
            tool_name="run_command",
            operation="command.execute",
            arguments={"cmd_array": ["pytest", "-q"], "timeout": 60},
            summary="Run the project test suite.",
        )
        return {"status": "COMPLETED", "authorization": authorization}


async def test_pipeline_pauses_approves_and_resumes(api_client) -> None:
    """A risky action pauses durably, then consumes one approval on resume."""
    headers, project_id, user_id = await _register_project(api_client)
    queued = await api_client.post(
        f"/api/v1/projects/{project_id}/instructions",
        headers=headers,
        json={"prompt": "Run tests with approval"},
    )
    instruction_id = queued.json()["id"]
    orchestrator = PipelineOrchestrator(project_id=project_id)

    async def load_agents() -> list[CommandAgent]:
        return [CommandAgent()]

    orchestrator._load_agents = load_agents  # type: ignore[method-assign]
    try:
        waiting = await orchestrator.run_pipeline(
            instruction_id,
            "Run tests with approval",
            user_id=user_id,
        )
        assert waiting["status"] == "WAITING_APPROVAL"
        approval_id = waiting["agent_runs"][0]["approval_id"]

        async with AsyncSessionLocal() as db:
            instruction = await db.get(Instruction, instruction_id)
            approval = await db.get(ApprovalRequest, approval_id)
        assert instruction is not None
        assert instruction.status == "WAITING_APPROVAL"
        assert approval is not None
        assert approval.status == "PENDING"
        assert approval.request_payload["cmd_array"] == ["pytest", "-q"]

        approved = await api_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=headers,
            json={"comment": "Tests are safe to run."},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "APPROVED"

        resumed = await orchestrator.run_pipeline(
            instruction_id,
            "Run tests with approval",
            user_id=user_id,
        )
        assert resumed["status"] == "COMPLETED"
        assert resumed["agent_runs"][0]["authorization"].startswith(
            "approval:"
        )
        async with AsyncSessionLocal() as db:
            approval = await db.get(ApprovalRequest, approval_id)
        assert approval is not None
        assert approval.consumed_at is not None
    finally:
        deleted = await api_client.delete(
            f"/api/v1/projects/{project_id}",
            headers=headers,
        )
        assert deleted.status_code == 200, deleted.text


async def test_cross_user_cannot_view_or_decide_approval(api_client) -> None:
    """Approval records and decisions remain scoped to the project owner."""
    owner_headers, project_id, user_id = await _register_project(api_client)
    intruder_headers, intruder_project_id, _ = await _register_project(api_client)
    instruction_id = f"approval_{uuid.uuid4().hex}"
    try:
        async with AsyncSessionLocal() as db:
            db.add(
                Instruction(
                    id=instruction_id,
                    project_id=project_id,
                    user_id=user_id,
                    prompt="Delete a file",
                    status="RUNNING",
                )
            )
            await db.commit()
            project = await db.get(Project, project_id)
        assert project is not None
        with pytest.raises(ApprovalRequiredError) as raised:
            await authorize_tool(
                project=project,
                user_id=user_id,
                instruction_id=instruction_id,
                tool_name="delete_file",
                operation="filesystem.delete",
                arguments={"path": "old.txt"},
                summary="Delete old.txt.",
            )
        approval_id = getattr(raised.value, "approval_id")

        hidden = await api_client.get(
            f"/api/v1/projects/{project_id}/approvals",
            headers=intruder_headers,
        )
        denied = await api_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=intruder_headers,
            json={},
        )
        assert hidden.status_code == 404
        assert denied.status_code == 404
    finally:
        for headers, target in (
            (owner_headers, project_id),
            (intruder_headers, intruder_project_id),
        ):
            deleted = await api_client.delete(
                f"/api/v1/projects/{target}",
                headers=headers,
            )
            assert deleted.status_code == 200, deleted.text


async def test_never_mode_auto_authorizes_allowed_command(api_client) -> None:
    """Explicit NEVER mode grants allowed commands without an approval row."""
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"approval_{uuid.uuid4().hex}"
    try:
        updated = await api_client.patch(
            f"/api/v1/projects/{project_id}",
            headers=headers,
            json={"approval_mode": "NEVER"},
        )
        assert updated.status_code == 200, updated.text
        async with AsyncSessionLocal() as db:
            project = await db.get(Project, project_id)
        assert project is not None
        grant = await authorize_tool(
            project=project,
            user_id=user_id,
            instruction_id=instruction_id,
            tool_name="run_command",
            operation="command.execute",
            arguments={"cmd_array": ["pytest", "-q"], "timeout": 60},
            summary="Run tests.",
        )
        assert grant.startswith("policy:")
        async with AsyncSessionLocal() as db:
            approvals = await db.scalars(
                select(ApprovalRequest).where(
                    ApprovalRequest.project_id == project_id
                )
            )
        assert approvals.all() == []
    finally:
        deleted = await api_client.delete(
            f"/api/v1/projects/{project_id}",
            headers=headers,
        )
        assert deleted.status_code == 200, deleted.text
