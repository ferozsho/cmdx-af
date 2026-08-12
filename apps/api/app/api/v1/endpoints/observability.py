"""Observability metrics endpoint for agent pipeline analytics."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.agent_run import AgentRun
from app.models.approval import ApprovalRequest
from app.models.git_commit import GitCommit
from app.models.instruction import Instruction
from app.models.llm_usage import LLMUsage
from app.models.project import Project
from app.models.user import User
from app.models.verification_run import VerificationRun

router = APIRouter()


@router.get("/observability/agent-metrics")
async def get_agent_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return real per-agent duration metrics and LLM usage aggregates."""
    result = await db.execute(
        select(
            AgentRun.agent_name,
            func.count(AgentRun.id),
            func.avg(AgentRun.duration_seconds),
            func.max(AgentRun.created_at),
        )
        .join(Instruction, Instruction.id == AgentRun.instruction_id)
        .where(Instruction.user_id == current_user.id)
        .group_by(AgentRun.agent_name)
        .order_by(AgentRun.agent_name)
    )
    agents = [
        {
            "name": name,
            "runs": int(runs),
            "avg_duration_seconds": round(float(avg_duration or 0), 2),
            "last_run": last_run.isoformat() if last_run else None,
        }
        for name, runs, avg_duration, last_run in result.all()
    ]

    total_result = await db.execute(
        select(func.count(AgentRun.id), func.avg(AgentRun.duration_seconds))
        .join(Instruction, Instruction.id == AgentRun.instruction_id)
        .where(Instruction.user_id == current_user.id)
    )
    total_runs, avg_all = total_result.one()

    # LLM usage aggregates from llm_usage
    usage_result = await db.execute(
        select(
            func.count(LLMUsage.id),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0),
            func.coalesce(func.sum(LLMUsage.cost), 0.0),
            func.count(func.distinct(LLMUsage.model)),
        ).where(
            LLMUsage.project_id.in_(
                select(Project.id).where(Project.user_id == current_user.id)
            )
        )
    )
    usage_calls, usage_tokens, usage_cost, usage_models = usage_result.one()

    queue_rows = await db.execute(
        select(Instruction.status, func.count(Instruction.id))
        .where(Instruction.user_id == current_user.id)
        .group_by(Instruction.status)
    )
    queue = {status: int(count) for status, count in queue_rows.all()}
    project_ids = select(Project.id).where(Project.user_id == current_user.id)
    pending_approvals = await db.scalar(
        select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.user_id == current_user.id,
            ApprovalRequest.status == "PENDING",
        )
    )
    verification_rows = await db.execute(
        select(VerificationRun.status, func.count(VerificationRun.id))
        .where(VerificationRun.project_id.in_(project_ids))
        .group_by(VerificationRun.status)
    )
    verification = {
        status: int(count) for status, count in verification_rows.all()
    }
    ai_commits = await db.scalar(
        select(func.count(GitCommit.id)).where(
            GitCommit.project_id.in_(project_ids),
            GitCommit.ai_generated.is_(True),
        )
    )

    return {
        "agents": agents,
        "total_runs": int(total_runs or 0),
        "avg_duration_seconds": round(float(avg_all or 0), 2),
        "llm_usage": {
            "calls": int(usage_calls or 0),
            "total_tokens": int(usage_tokens or 0),
            "cost": round(float(usage_cost or 0), 6),
            "models": int(usage_models or 0),
        },
        "queue": queue,
        "pending_approvals": int(pending_approvals or 0),
        "verification": verification,
        "ai_commits": int(ai_commits or 0),
    }
