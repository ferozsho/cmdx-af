"""Integration tests for the durable multi-agent orchestration pipeline."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import delete, func, select

from app.agents.pipeline import PipelineOrchestrator
from app.agents.registry import AGENT_REGISTRY, DEFAULT_AGENT_ORDER
from app.core.database import AsyncSessionLocal
from app.models.agent_run import AgentRun
from app.models.artifact import Artifact
from app.models.instruction import Instruction
from app.models.project import Project
from app.models.user import User
from app.services.approvals import ApprovalRequiredError


class FakeAgent:
    """Small deterministic agent used to verify orchestration behavior."""

    def __init__(
        self,
        name: str,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
        on_execute: Callable[[], None] | None = None,
    ) -> None:
        self.agent_name = name
        self._result = result or {"status": "COMPLETED"}
        self._error = error
        self._on_execute = on_execute

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        if self._on_execute:
            self._on_execute()
        if self._error:
            raise self._error
        return dict(self._result)


async def _create_instruction() -> tuple[str, str, str]:
    """Create an isolated user, project, and instruction for a pipeline test."""
    suffix = uuid.uuid4().hex
    user_id = f"user_{suffix}"
    project_id = f"project_{suffix}"
    instruction_id = f"instruction_{suffix}"
    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=user_id,
                email=f"pipeline-{suffix}@mailinator.com",
                hashed_password="unused-test-hash",
                full_name="Pipeline Test",
            )
        )
        session.add(
            Project(
                id=project_id,
                user_id=user_id,
                name="Pipeline Test Project",
            )
        )
        session.add(
            Instruction(
                id=instruction_id,
                project_id=project_id,
                user_id=user_id,
                prompt="Test the pipeline",
                status="RUNNING",
            )
        )
        await session.commit()
    return user_id, project_id, instruction_id


async def _cleanup_instruction(
    user_id: str,
    project_id: str,
    instruction_id: str,
) -> None:
    """Remove pipeline test rows in foreign-key-safe order."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Artifact).where(Artifact.instruction_id == instruction_id)
        )
        await session.execute(
            delete(AgentRun).where(AgentRun.instruction_id == instruction_id)
        )
        await session.execute(
            delete(Instruction).where(Instruction.id == instruction_id)
        )
        await session.execute(delete(Project).where(Project.id == project_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_pipeline_persists_success_and_survives_event_failure() -> None:
    """Successful steps and final state persist even if the event client drops."""
    user_id, project_id, instruction_id = await _create_instruction()
    orchestrator = PipelineOrchestrator(project_id=project_id)

    async def load_agents() -> list[FakeAgent]:
        return [
            FakeAgent("First Agent"),
            FakeAgent("Second Agent", {"status": "completed", "answer": 42}),
        ]

    async def disconnected_callback(*args: Any, **kwargs: Any) -> None:
        raise ConnectionError("client disconnected")

    orchestrator._load_agents = load_agents  # type: ignore[method-assign]
    try:
        result = await orchestrator.run_pipeline(
            instruction_id,
            "Test the pipeline",
            event_callback=disconnected_callback,
        )
        assert result["status"] == "COMPLETED"
        assert [run["status"] for run in result["agent_runs"]] == [
            "COMPLETED",
            "COMPLETED",
        ]

        async with AsyncSessionLocal() as session:
            instruction = await session.get(Instruction, instruction_id)
            run_count = await session.scalar(
                select(func.count(AgentRun.id)).where(
                    AgentRun.instruction_id == instruction_id
                )
            )
        assert instruction is not None
        assert instruction.status == "COMPLETED"
        assert run_count == 2
    finally:
        await _cleanup_instruction(user_id, project_id, instruction_id)


@pytest.mark.asyncio
async def test_pipeline_stops_and_persists_failure() -> None:
    """An agent exception fails the job and prevents later agents from running."""
    user_id, project_id, instruction_id = await _create_instruction()
    orchestrator = PipelineOrchestrator(project_id=project_id)
    second_agent_ran = False

    def mark_second_agent() -> None:
        nonlocal second_agent_ran
        second_agent_ran = True

    async def load_agents() -> list[FakeAgent]:
        return [
            FakeAgent("Failing Agent", error=RuntimeError("planned failure")),
            FakeAgent("Skipped Agent", on_execute=mark_second_agent),
        ]

    orchestrator._load_agents = load_agents  # type: ignore[method-assign]
    try:
        result = await orchestrator.run_pipeline(
            instruction_id,
            "Test the failure path",
        )
        assert result["status"] == "FAILED"
        assert len(result["agent_runs"]) == 1
        assert result["agent_runs"][0]["status"] == "FAILED"
        assert second_agent_ran is False

        async with AsyncSessionLocal() as session:
            instruction = await session.get(Instruction, instruction_id)
            run_status = await session.scalar(
                select(AgentRun.status).where(
                    AgentRun.instruction_id == instruction_id
                )
            )
        assert instruction is not None
        assert instruction.status == "FAILED"
        assert run_status == "FAILED"
    finally:
        await _cleanup_instruction(user_id, project_id, instruction_id)


def test_registry_contains_every_required_specialized_agent() -> None:
    """The default pipeline exposes every Phase 7 specialized role in order."""
    required = [
        "Planning Agent",
        "Architecture Agent",
        "UI/UX Agent",
        "Frontend Agent",
        "Backend Agent",
        "Database Agent",
        "Documentation Agent",
        "Test Agent",
        "Validation Agent",
        "Git Agent",
    ]

    assert all(name in AGENT_REGISTRY for name in required)
    assert [name for name in DEFAULT_AGENT_ORDER if name in required] == required


@pytest.mark.asyncio
async def test_pipeline_resumes_from_completed_checkpoint() -> None:
    """A retried pipeline skips durable completed steps and continues in order."""
    user_id, project_id, instruction_id = await _create_instruction()
    orchestrator = PipelineOrchestrator(project_id=project_id)
    first_agent_ran = False

    def mark_first_agent() -> None:
        nonlocal first_agent_ran
        first_agent_ran = True

    async def load_agents() -> list[FakeAgent]:
        return [
            FakeAgent("First Agent", on_execute=mark_first_agent),
            FakeAgent("Second Agent", {"status": "COMPLETED", "continued": True}),
        ]

    orchestrator._load_agents = load_agents  # type: ignore[method-assign]
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                AgentRun(
                    instruction_id=instruction_id,
                    agent_name="First Agent",
                    status="COMPLETED",
                    output='{"checkpoint": true}',
                    metadata_json={
                        "status": "COMPLETED",
                        "agent_name": "First Agent",
                        "checkpoint": True,
                    },
                )
            )
            await session.commit()

        result = await orchestrator.run_pipeline(
            instruction_id,
            "Resume the pipeline",
        )

        assert result["status"] == "COMPLETED"
        assert first_agent_ran is False
        assert result["agent_runs"][0]["checkpoint"] is True
        assert result["agent_runs"][1]["continued"] is True
    finally:
        await _cleanup_instruction(user_id, project_id, instruction_id)


@pytest.mark.asyncio
async def test_pipeline_pauses_for_human_confirmation() -> None:
    """A risky agent action produces a durable non-terminal approval state."""
    user_id, project_id, instruction_id = await _create_instruction()
    orchestrator = PipelineOrchestrator(project_id=project_id)

    async def load_agents() -> list[FakeAgent]:
        return [
            FakeAgent(
                "Risky Agent",
                error=ApprovalRequiredError("approval-test", "Approve mutation"),
            ),
            FakeAgent("Must Not Run"),
        ]

    orchestrator._load_agents = load_agents  # type: ignore[method-assign]
    try:
        result = await orchestrator.run_pipeline(
            instruction_id,
            "Require approval",
        )

        assert result["status"] == "WAITING_APPROVAL"
        assert len(result["agent_runs"]) == 1
        assert result["agent_runs"][0]["approval_id"] == "approval-test"
        async with AsyncSessionLocal() as session:
            instruction = await session.get(Instruction, instruction_id)
        assert instruction is not None
        assert instruction.status == "WAITING_APPROVAL"
    finally:
        await _cleanup_instruction(user_id, project_id, instruction_id)


@pytest.mark.asyncio
async def test_pipeline_honors_cancellation_between_steps() -> None:
    """Cancellation is checked before each step and prevents tool execution."""
    user_id, project_id, instruction_id = await _create_instruction()
    orchestrator = PipelineOrchestrator(project_id=project_id)
    agent_ran = False

    def mark_agent() -> None:
        nonlocal agent_ran
        agent_ran = True

    async def load_agents() -> list[FakeAgent]:
        return [FakeAgent("Cancelled Agent", on_execute=mark_agent)]

    async def cancel_check() -> bool:
        return True

    orchestrator._load_agents = load_agents  # type: ignore[method-assign]
    try:
        result = await orchestrator.run_pipeline(
            instruction_id,
            "Cancel the pipeline",
            cancel_check=cancel_check,
        )

        assert result["status"] == "CANCELLED"
        assert agent_ran is False
        async with AsyncSessionLocal() as session:
            instruction = await session.get(Instruction, instruction_id)
        assert instruction is not None
        assert instruction.status == "CANCELLED"
    finally:
        await _cleanup_instruction(user_id, project_id, instruction_id)
