"""Human approval inbox and decision endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.approval import ApprovalRequest
from app.models.instruction import Instruction
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.services.instruction_events import append_instruction_event
from app.services.rate_limit import api_rate_limit

router = APIRouter()


class ApprovalDecision(BaseModel):
    """Optional audit comment supplied with a decision."""

    comment: str | None = Field(default=None, max_length=2000)


def _approval_payload(approval: ApprovalRequest) -> dict[str, Any]:
    return {
        "id": approval.id,
        "project_id": approval.project_id,
        "instruction_id": approval.instruction_id,
        "tool_name": approval.tool_name,
        "operation": approval.operation,
        "risk_level": approval.risk_level,
        "summary": approval.summary,
        "request_payload": approval.request_payload,
        "status": approval.status,
        "requested_at": approval.requested_at.isoformat(),
        "expires_at": approval.expires_at.isoformat(),
        "decided_at": (
            approval.decided_at.isoformat() if approval.decided_at else None
        ),
        "decision_comment": approval.decision_comment,
    }


@router.get("/projects/{project_id}/approvals")
async def list_approvals(
    project_id: str,
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List approval history for an owned project."""
    if not await ProjectRepository(db).belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    query = select(ApprovalRequest).where(
        ApprovalRequest.project_id == project_id,
        ApprovalRequest.user_id == current_user.id,
    )
    if status:
        query = query.where(ApprovalRequest.status == status.upper())
    approvals = await db.scalars(
        query.order_by(ApprovalRequest.requested_at.desc()).limit(100)
    )
    return [_approval_payload(item) for item in approvals.all()]


async def _decide(
    approval_id: str,
    decision: str,
    data: ApprovalDecision,
    db: AsyncSession,
    current_user: User,
) -> dict[str, Any]:
    approval = await db.scalar(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.user_id == current_user.id,
        )
        .with_for_update()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != "PENDING":
        return _approval_payload(approval)
    now = datetime.now(UTC).replace(tzinfo=None)
    if approval.expires_at < now:
        approval.status = "EXPIRED"
        await db.commit()
        raise HTTPException(status_code=409, detail="Approval request expired")

    approval.status = decision
    approval.decided_at = now
    approval.decided_by = current_user.id
    approval.decision_comment = data.comment
    instruction = (
        await db.get(Instruction, approval.instruction_id)
        if approval.instruction_id
        else None
    )
    if instruction and instruction.status == "WAITING_APPROVAL":
        if decision == "APPROVED":
            instruction.status = "PENDING"
            instruction.available_at = now
            instruction.last_error = None
            event_status = "APPROVED"
            message = "Approval granted; instruction requeued."
        else:
            instruction.status = "CANCELLED"
            instruction.finished_at = now
            event_status = "REJECTED"
            message = "Approval rejected; instruction cancelled."
        await append_instruction_event(
            approval.project_id,
            instruction.id,
            {
                "instruction_id": instruction.id,
                "agent_name": "System",
                "status": event_status,
                "message": message,
                "data": {"approval_id": approval.id},
            },
            db,
        )
    await db.commit()
    await db.refresh(approval)
    return _approval_payload(approval)


@router.post("/approvals/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    data: ApprovalDecision,
    _rate_limit_guard: None = Depends(api_rate_limit("approvals")),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Approve a pending request and resume its instruction."""
    return await _decide(approval_id, "APPROVED", data, db, current_user)


@router.post("/approvals/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    data: ApprovalDecision,
    _rate_limit_guard: None = Depends(api_rate_limit("approvals")),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Reject a pending request and cancel its instruction."""
    return await _decide(approval_id, "REJECTED", data, db, current_user)
