"""Durable instruction submission, history, and cancellation endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.agent_run import AgentRun
from app.models.instruction import Instruction
from app.models.session import Session
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.services.instruction_events import append_instruction_event
from app.services.rate_limit import api_rate_limit

router = APIRouter()


async def _require_project_owner(
    project_id: str,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Return 404 unless the authenticated user owns the project."""
    if not await ProjectRepository(db).belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")


class InstructionSubmit(BaseModel):
    """Instruction submission request payload."""

    prompt: str = Field(min_length=1, max_length=100000)
    image_bytes: str | None = None
    image_mime_type: str | None = None
    session_id: str | None = None


class InstructionResponse(BaseModel):
    """Instruction queue state returned to clients."""

    id: str
    project_id: str
    user_id: str | None = None
    prompt: str
    status: str
    created_at: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    cancel_requested_at: str | None = None


class UserInstructionItem(BaseModel):
    """Lightweight instruction for user-wide history cycling."""

    id: str
    prompt: str
    project_id: str
    created_at: str | None = None


class InstructionDetailResponse(BaseModel):
    """Detailed instruction with persisted agent runs."""

    id: str
    project_id: str
    user_id: str | None = None
    prompt: str
    status: str
    created_at: str | None = None
    runs: list[dict] = Field(default_factory=list)


def _instruction_response(instruction: Instruction) -> InstructionResponse:
    """Serialize queue state consistently for all endpoints."""
    return InstructionResponse(
        id=instruction.id,
        project_id=instruction.project_id,
        user_id=instruction.user_id,
        prompt=instruction.prompt,
        status=instruction.status,
        created_at=(
            instruction.created_at.isoformat()
            if instruction.created_at
            else None
        ),
        attempt_count=instruction.attempt_count,
        max_attempts=instruction.max_attempts,
        cancel_requested_at=(
            instruction.cancel_requested_at.isoformat()
            if instruction.cancel_requested_at
            else None
        ),
    )


@router.get(
    "/users/me/instructions",
    response_model=list[UserInstructionItem],
)
async def list_user_instructions(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List recent instructions across all projects for the current user."""
    result = await db.execute(
        select(Instruction)
        .where(Instruction.user_id == current_user.id)
        .order_by(Instruction.created_at.desc())
        .limit(limit)
    )
    return [
        UserInstructionItem(
            id=item.id,
            prompt=item.prompt,
            project_id=item.project_id,
            created_at=(
                item.created_at.isoformat() if item.created_at else None
            ),
        )
        for item in result.scalars().all()
    ]


@router.get(
    "/projects/{project_id}/instructions",
    response_model=list[InstructionResponse],
)
async def list_instructions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List recent instruction queue states for an owned project."""
    await _require_project_owner(project_id, current_user, db)
    result = await db.execute(
        select(Instruction)
        .where(Instruction.project_id == project_id)
        .order_by(Instruction.created_at.desc())
        .limit(50)
    )
    return [_instruction_response(item) for item in result.scalars().all()]


@router.get(
    "/projects/{project_id}/instructions/history",
    response_model=list[InstructionDetailResponse],
)
async def list_instruction_history(
    project_id: str,
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    agent_name: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List instruction history with optional agent and date filters."""
    await _require_project_owner(project_id, current_user, db)
    query = (
        select(Instruction)
        .where(Instruction.project_id == project_id)
        .options(selectinload(Instruction.runs))
    )
    if agent_name:
        query = query.where(
            Instruction.id.in_(
                select(AgentRun.instruction_id).where(
                    AgentRun.agent_name == agent_name
                )
            )
        )
    if date_from:
        try:
            query = query.where(
                Instruction.created_at >= datetime.fromisoformat(date_from)
            )
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="date_from must be an ISO-8601 datetime",
            ) from None
    if date_to:
        try:
            query = query.where(
                Instruction.created_at <= datetime.fromisoformat(date_to)
            )
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="date_to must be an ISO-8601 datetime",
            ) from None
    result = await db.execute(
        query.order_by(Instruction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [
        InstructionDetailResponse(
            id=item.id,
            project_id=item.project_id,
            user_id=item.user_id,
            prompt=item.prompt,
            status=item.status,
            created_at=(
                item.created_at.isoformat() if item.created_at else None
            ),
            runs=[
                {
                    "agent_name": run.agent_name,
                    "status": run.status,
                    "duration_seconds": run.duration_seconds,
                    "output": run.output,
                    "metadata": run.metadata_json,
                    "created_at": (
                        run.created_at.isoformat() if run.created_at else None
                    ),
                }
                for run in item.runs
            ],
        )
        for item in result.scalars().all()
    ]


@router.post(
    "/projects/{project_id}/instructions",
    response_model=InstructionResponse,
    status_code=202,
)
async def submit_instruction(
    project_id: str,
    data: InstructionSubmit,
    _rate_limit_guard: None = Depends(api_rate_limit("instructions")),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=200,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Durably enqueue an instruction, deduplicated by Idempotency-Key."""
    await _require_project_owner(project_id, current_user, db)
    normalized_key = idempotency_key.strip() if idempotency_key else None
    if normalized_key:
        existing_result = await db.execute(
            select(Instruction).where(
                Instruction.project_id == project_id,
                Instruction.idempotency_key == normalized_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return _instruction_response(existing)

    if data.session_id:
        session = await db.get(Session, data.session_id)
        if (
            not session
            or session.project_id != project_id
            or session.user_id != current_user.id
        ):
            raise HTTPException(status_code=404, detail="Session not found")

    instruction = Instruction(
        id=f"ins_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        user_id=current_user.id,
        session_id=data.session_id,
        prompt=data.prompt,
        image_data=data.image_bytes,
        image_mime_type=data.image_mime_type,
        status="PENDING",
        idempotency_key=normalized_key,
    )
    db.add(instruction)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        if not normalized_key:
            raise
        duplicate_result = await db.execute(
            select(Instruction).where(
                Instruction.project_id == project_id,
                Instruction.idempotency_key == normalized_key,
            )
        )
        return _instruction_response(duplicate_result.scalar_one())

    await append_instruction_event(
        project_id,
        instruction.id,
        {
            "instruction_id": instruction.id,
            "agent_name": "System",
            "status": "PENDING",
            "message": "Instruction queued for durable execution.",
        },
        db,
    )
    await db.commit()
    await db.refresh(instruction)
    return _instruction_response(instruction)


@router.post(
    "/projects/{project_id}/instructions/{instruction_id}/cancel",
    response_model=InstructionResponse,
)
async def cancel_instruction(
    project_id: str,
    instruction_id: str,
    _rate_limit_guard: None = Depends(api_rate_limit("instructions")),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Idempotently request cancellation of a queued or running instruction."""
    await _require_project_owner(project_id, current_user, db)
    instruction = await db.get(Instruction, instruction_id)
    if not instruction or instruction.project_id != project_id:
        raise HTTPException(status_code=404, detail="Instruction not found")
    if instruction.status not in {"COMPLETED", "FAILED", "CANCELLED"}:
        instruction.cancel_requested_at = (
            instruction.cancel_requested_at or datetime.now(UTC).replace(tzinfo=None)
        )
        if instruction.status == "PENDING":
            instruction.status = "CANCELLED"
            instruction.finished_at = datetime.now(UTC).replace(tzinfo=None)
        await append_instruction_event(
            project_id,
            instruction_id,
            {
                "instruction_id": instruction_id,
                "agent_name": "System",
                "status": "CANCEL_REQUESTED",
                "message": "Cancellation requested.",
            },
            db,
        )
        await db.commit()
        await db.refresh(instruction)
    return _instruction_response(instruction)
