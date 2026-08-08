"""Instruction Submission and Agent Execution Endpoints."""

import asyncio
import uuid
from typing import Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.pipeline import PipelineOrchestrator
from app.core.database import get_db
from app.repositories.project_repo import ProjectRepository
from app.repositories.device_repo import DeviceRepository
from app.services.sse_broadcaster import broadcaster

router = APIRouter()


class InstructionSubmit(BaseModel):
    """Instruction submission request payload."""

    prompt: str


class InstructionResponse(BaseModel):
    """Instruction response schema."""

    id: str
    project_id: str
    prompt: str
    status: str


@router.get(
    "/projects/{project_id}/instructions",
    response_model=List[InstructionResponse],
)
async def list_instructions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List recent instructions for a project with their status."""
    from sqlalchemy import select

    from app.models.instruction import Instruction

    result = await db.execute(
        select(Instruction)
        .where(Instruction.project_id == project_id)
        .order_by(Instruction.created_at.desc())
        .limit(50)
    )
    return [
        InstructionResponse(
            id=i.id,
            project_id=i.project_id,
            prompt=i.prompt,
            status=i.status,
        )
        for i in result.scalars().all()
    ]


def _resolve_device_and_workspace(
    project_id: str,
) -> tuple[str, str]:
    """Resolve device/workspace IDs from project context (sync-safe defaults)."""
    return ("dev_feroz_pc", "ws-test")


@router.post(
    "/projects/{project_id}/instructions",
    response_model=InstructionResponse,
)
async def submit_instruction(
    project_id: str,
    data: InstructionSubmit,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit natural language development instruction and trigger Agent Pipeline."""
    ins_id = f"ins_{uuid.uuid4().hex[:8]}"

    # Resolve device and workspace for this project
    device_id = "dev_feroz_pc"
    workspace_id = "ws-test"
    try:
        repo = ProjectRepository(db)
        project = await repo.get_by_id(project_id)
        if project:
            # Look up the first workspace for this project
            from sqlalchemy import select
            from app.models.workspace import Workspace
            result = await db.execute(
                select(Workspace).where(Workspace.project_id == project_id).limit(1)
            )
            ws = result.scalar_one_or_none()
            if ws:
                workspace_id = ws.id
                if ws.device_id:
                    device_id = ws.device_id
    except Exception:
        pass

    async def _run_async_pipeline() -> None:
        orchestrator = PipelineOrchestrator()

        async def _event_cb(
            agent_name: str,
            status: str,
            msg: str,
            data: dict | None = None,
        ) -> None:
            payload: dict = {
                "instruction_id": ins_id,
                "agent_name": agent_name,
                "status": status,
                "message": msg,
            }
            if data:
                payload["data"] = data
            await broadcaster.broadcast(project_id, payload)

        await orchestrator.run_pipeline(
            ins_id,
            data.prompt,
            event_callback=_event_cb,
            device_id=device_id,
            workspace_id=workspace_id,
        )

    asyncio.create_task(_run_async_pipeline())

    return InstructionResponse(
        id=ins_id,
        project_id=project_id,
        prompt=data.prompt,
        status="RUNNING",
    )
