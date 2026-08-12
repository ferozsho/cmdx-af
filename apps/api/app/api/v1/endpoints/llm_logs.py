"""LLM interaction log retrieval endpoints — per-project audit trail."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.instruction import Instruction
from app.models.llm_usage import LLMUsage
from app.models.project import Project
from app.models.user import User

router = APIRouter()


async def _build_log_item(
    r: LLMUsage, db: AsyncSession, prompt_cache: dict[str, str]
) -> dict:
    """Build a log dict, falling back to instructions.prompt for old rows."""
    prompt_text = r.prompt_text
    if not prompt_text and r.instruction_id:
        # Check cache first
        if r.instruction_id in prompt_cache:
            prompt_text = prompt_cache[r.instruction_id]
        else:
            inst = await db.get(Instruction, r.instruction_id)
            if inst and inst.prompt:
                prompt_text = inst.prompt
                prompt_cache[r.instruction_id] = inst.prompt

    return {
        "id": r.id,
        "instruction_id": r.instruction_id,
        "project_id": r.project_id,
        "provider": r.provider,
        "model": r.model,
        "prompt_text": prompt_text,
        "system_prompt_text": r.system_prompt_text,
        "response_text": r.response_text,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "total_tokens": r.total_tokens,
        "cost": r.cost,
        "duration_ms": r.duration_ms,
        "status": r.status,
        "error_message": r.error_message,
        "request_id": r.request_id,
        "temperature": r.temperature,
        "json_mode": r.json_mode,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/projects/{project_id}/llm-logs")
async def list_llm_logs(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    provider: str | None = Query(None),
    model: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List LLM call logs for a project with pagination and filters.

    Content is secret-redacted and bounded when written. Older rows fall back
    to the owning instruction prompt when no stored prompt is available.
    """
    # Verify project exists and belongs to the current user
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build base query
    query = select(LLMUsage).where(LLMUsage.project_id == project_id)

    if status:
        query = query.where(LLMUsage.status == status)
    if provider:
        query = query.where(LLMUsage.provider == provider)
    if model:
        query = query.where(LLMUsage.model == model)

    # Sorting
    sort_col = getattr(LLMUsage, sort_by, LLMUsage.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Count total (before pagination)
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total = (await db.execute(count_query)).scalar() or 0

    # Fetch page
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    prompt_cache: dict[str, str] = {}
    items = [
        await _build_log_item(r, db, prompt_cache) for r in rows
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/projects/{project_id}/llm-logs/{log_id}")
async def get_llm_log(
    project_id: str,
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get a single LLM call log by ID with full detail."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    log = await db.get(LLMUsage, log_id)
    if not log or log.project_id != project_id:
        raise HTTPException(status_code=404, detail="Log entry not found")

    # Fallback prompt_text from instructions for old rows
    prompt_text = log.prompt_text
    if not prompt_text and log.instruction_id:
        inst = await db.get(Instruction, log.instruction_id)
        if inst and inst.prompt:
            prompt_text = inst.prompt

    return {
        "id": log.id,
        "instruction_id": log.instruction_id,
        "project_id": log.project_id,
        "provider": log.provider,
        "model": log.model,
        "prompt_text": prompt_text,
        "system_prompt_text": log.system_prompt_text,
        "response_text": log.response_text,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "cost": log.cost,
        "duration_ms": log.duration_ms,
        "status": log.status,
        "error_message": log.error_message,
        "request_id": log.request_id,
        "temperature": log.temperature,
        "json_mode": log.json_mode,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("/projects/{project_id}/llm-logs/stats")
async def get_llm_log_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get aggregate LLM usage stats for a project."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(
            func.count(LLMUsage.id),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0),
            func.coalesce(func.sum(LLMUsage.cost), 0.0),
            func.coalesce(func.sum(LLMUsage.duration_ms), 0),
            func.count(func.distinct(LLMUsage.model)),
            func.count(func.distinct(LLMUsage.provider)),
        ).where(
            LLMUsage.project_id == project_id,
            LLMUsage.status == "success",
        )
    )
    (
        total_calls,
        total_tokens,
        total_cost,
        total_duration_ms,
        unique_models,
        unique_providers,
    ) = result.one()

    error_result = await db.execute(
        select(func.count(LLMUsage.id)).where(
            LLMUsage.project_id == project_id,
            LLMUsage.status == "error",
        )
    )
    error_count = error_result.scalar() or 0

    return {
        "total_calls": int(total_calls or 0),
        "error_count": int(error_count or 0),
        "total_tokens": int(total_tokens or 0),
        "total_cost": round(float(total_cost or 0), 6),
        "total_duration_ms": int(total_duration_ms or 0),
        "unique_models": int(unique_models or 0),
        "unique_providers": int(unique_providers or 0),
    }
