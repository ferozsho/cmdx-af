"""Observability metrics endpoint for agent pipeline analytics."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent_run import AgentRun

router = APIRouter()


@router.get("/observability/agent-metrics")
async def get_agent_metrics(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return real per-agent duration/status metrics from agent_runs."""
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

    return {
        "agents": agents,
        "total_runs": int(total_runs or 0),
        "avg_duration_seconds": round(float(avg_all or 0), 2),
    }
