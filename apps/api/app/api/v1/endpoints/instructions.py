"""Instruction Submission and Agent Execution Endpoints."""

import asyncio
import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.pipeline import PipelineOrchestrator
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.repositories.device_repo import DeviceRepository
from app.services.sse_broadcaster import broadcaster

router = APIRouter()


class InstructionSubmit(BaseModel):
    """Instruction submission request payload."""

    prompt: str
    image_bytes: Optional[str] = None
    image_mime_type: Optional[str] = None
    session_id: Optional[str] = None


class InstructionResponse(BaseModel):
    """Instruction response schema."""

    id: str
    project_id: str
    user_id: str | None = None
    prompt: str
    status: str
    created_at: str | None = None


class UserInstructionItem(BaseModel):
    """Lightweight instruction for user-wide history cycling."""

    id: str
    prompt: str
    project_id: str
    created_at: str | None = None


class InstructionDetailResponse(BaseModel):
    """Detailed instruction with agent runs for history view."""

    id: str
    project_id: str
    user_id: str | None = None
    prompt: str
    status: str
    created_at: str | None = None
    runs: list[dict] = []


@router.get(
    "/users/me/instructions",
    response_model=List[UserInstructionItem],
)
async def list_user_instructions(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List recent instructions across all projects for the current user."""
    from sqlalchemy import select
    from app.models.instruction import Instruction

    result = await db.execute(
        select(Instruction)
        .where(Instruction.user_id == current_user.id)
        .order_by(Instruction.created_at.desc())
        .limit(limit)
    )
    return [
        UserInstructionItem(
            id=i.id,
            prompt=i.prompt,
            project_id=i.project_id,
            created_at=i.created_at.isoformat() if i.created_at else None,
        )
        for i in result.scalars().all()
    ]


@router.get(
    "/projects/{project_id}/instructions",
    response_model=List[InstructionResponse],
)
async def list_instructions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
            user_id=i.user_id,
            prompt=i.prompt,
            status=i.status,
            created_at=i.created_at.isoformat() if i.created_at else None,
        )
        for i in result.scalars().all()
    ]


@router.get(
    "/projects/{project_id}/instructions/history",
    response_model=List[InstructionDetailResponse],
)
async def list_instruction_history(
    project_id: str,
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    agent_name: Optional[str] = Query(
        None, description="Filter by agent name (e.g. 'Test Agent')"
    ),
    date_from: Optional[str] = Query(
        None, description="Filter from date (ISO format, e.g. 2026-08-01)"
    ),
    date_to: Optional[str] = Query(
        None, description="Filter to date (ISO format)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List instructions with full agent run logs for history review.

    Supports pagination (limit/offset) and filtering by agent name and date
    range.
    """
    from datetime import datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.agent_run import AgentRun
    from app.models.instruction import Instruction

    # Build base query with eager-loaded runs
    query = (
        select(Instruction)
        .where(Instruction.project_id == project_id)
        .options(selectinload(Instruction.runs))
    )

    # Filter by agent name — join through agent_runs
    if agent_name:
        query = query.where(
            Instruction.id.in_(
                select(AgentRun.instruction_id).where(
                    AgentRun.agent_name == agent_name
                )
            )
        )

    # Filter by date range
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(Instruction.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(Instruction.created_at <= dt_to)
        except ValueError:
            pass

    # Order and paginate
    query = query.order_by(Instruction.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    instructions = result.scalars().all()
    return [
        InstructionDetailResponse(
            id=i.id,
            project_id=i.project_id,
            user_id=i.user_id,
            prompt=i.prompt,
            status=i.status,
            created_at=i.created_at.isoformat() if i.created_at else None,
            runs=[
                {
                    "agent_name": r.agent_name,
                    "status": r.status,
                    "duration_seconds": r.duration_seconds,
                    "output": r.output,
                    "metadata": r.metadata_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in (i.runs or [])
            ],
        )
        for i in instructions
    ]


def _resolve_device_and_workspace(
    project_id: str,
    project_local_path: str | None = None,
) -> tuple[str, str]:
    """Resolve device/workspace IDs from project context (sync-safe defaults)."""
    if project_local_path:
        return ("dev_feroz_pc", project_local_path)
    return ("dev_feroz_pc", "ws-test")


@router.post(
    "/projects/{project_id}/instructions",
    response_model=InstructionResponse,
)
async def submit_instruction(
    project_id: str,
    data: InstructionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Submit natural language development instruction and trigger Agent Pipeline."""
    from app.models.instruction import Instruction

    ins_id = f"ins_{uuid.uuid4().hex[:8]}"

    # Persist instruction immediately with user_id for query history
    instruction = Instruction(
        id=ins_id,
        project_id=project_id,
        user_id=current_user.id,
        session_id=data.session_id,
        prompt=data.prompt,
        image_data=data.image_bytes,
        status="RUNNING",
    )
    db.add(instruction)
    await db.commit()

    # Resolve device and workspace for this project
    device_id = "dev_feroz_pc"
    workspace_id = "ws-test"
    try:
        repo = ProjectRepository(db)
        project = await repo.get_by_id(project_id)
        if project and project.local_path:
            workspace_id = project.local_path
        elif project:
            # Look up the first workspace for this project
            from sqlalchemy import select
            from app.models.workspace import Workspace
            result = await db.execute(
                select(Workspace).where(Workspace.project_id == project_id).limit(1)
            )
            ws = result.scalar_one_or_none()
            if ws:
                workspace_id = ws.local_path or ws.id
                if ws.device_id:
                    device_id = ws.device_id
    except Exception:
        pass

    async def _run_async_pipeline() -> None:
        orchestrator = PipelineOrchestrator(project_id=project_id)

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

        # Build previous context from session if applicable
        previous_context: list[dict] = []
        session_model_name: str | None = None
        session_context_limit: int | None = None
        if data.session_id:
            try:
                from sqlalchemy import select as sa_select
                from sqlalchemy.orm import selectinload
                from app.models.session import Session as SessionModel
                from app.core.database import AsyncSessionLocal

                async with AsyncSessionLocal() as sdb:
                    sess = await sdb.get(SessionModel, data.session_id)
                    if sess and sess.project_id == project_id:
                        session_model_name = sess.model_name
                        session_context_limit = sess.context_limit
                        # Fetch last 5 completed instructions for context
                        result = await sdb.execute(
                            sa_select(Instruction)
                            .where(
                                Instruction.session_id == data.session_id,
                                Instruction.status.in_(
                                    ["COMPLETED", "FAILED"]
                                ),
                            )
                            .order_by(Instruction.created_at.desc())
                            .limit(5)
                        )
                        prev = result.scalars().all()
                        previous_context = [
                            {
                                "instruction_id": p.id,
                                "prompt": p.prompt,
                                "status": p.status,
                            }
                            for p in reversed(prev)
                        ]
            except Exception:
                pass

        await orchestrator.run_pipeline(
            ins_id,
            data.prompt,
            event_callback=_event_cb,
            device_id=device_id,
            workspace_id=workspace_id,
            image_bytes=data.image_bytes,
            image_mime_type=data.image_mime_type,
            previous_context=previous_context,
            session_model_name=session_model_name,
            session_context_limit=session_context_limit,
        )

    asyncio.create_task(_run_async_pipeline())

    return InstructionResponse(
        id=ins_id,
        project_id=project_id,
        user_id=current_user.id,
        prompt=data.prompt,
        status="RUNNING",
    )
