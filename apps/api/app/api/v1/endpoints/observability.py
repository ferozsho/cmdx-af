"""Observability metrics endpoint for agent pipeline analytics."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.agent_run import AgentRun
from app.models.llm_usage import LLMUsage
from app.models.user import User

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
    )
    total_runs, avg_all = total_result.one()

    # LLM usage aggregates from llm_usage
    usage_result = await db.execute(
        select(
            func.count(LLMUsage.id),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0),
            func.coalesce(func.sum(LLMUsage.cost), 0.0),
            func.count(func.distinct(LLMUsage.model)),
        )
    )
    usage_calls, usage_tokens, usage_cost, usage_models = usage_result.one()

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
    }
