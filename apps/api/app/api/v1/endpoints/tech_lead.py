"""Project-wide context and technical-lead assistant endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.llm.router import ModelRouter
from app.models.project import Project
from app.models.tech_lead_interaction import TechLeadInteraction
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.services.project_context import build_project_context
from app.services.rate_limit import api_rate_limit

router = APIRouter()


class TechLeadQuery(BaseModel):
    """A bounded question about an owned project."""

    question: str = Field(min_length=2, max_length=4000)


async def _owned_project(
    project_id: str,
    current_user: User,
    db: AsyncSession,
) -> Project:
    project = await ProjectRepository(db).get_by_id(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/context")
async def get_project_context(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Expose bounded project knowledge to the web UI and IDE clients."""
    project = await _owned_project(project_id, current_user, db)
    return await build_project_context(db, project)


@router.get("/projects/{project_id}/tasks")
async def list_project_tasks(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return manager-style task, agent-progress, and question queues."""
    project = await _owned_project(project_id, current_user, db)
    context = await build_project_context(db, project)
    return {
        "project_id": project.id,
        "tasks": context["instructions"],
        "agent_runs": context["agent_runs"],
        "questions": context["questions"],
    }


@router.post("/projects/{project_id}/tech-lead/query")
async def query_tech_lead(
    project_id: str,
    data: TechLeadQuery,
    _rate_limit_guard: None = Depends(api_rate_limit("tech-lead")),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Answer a project question from durable history and generated artifacts."""
    project = await _owned_project(project_id, current_user, db)
    context = await build_project_context(
        db, project, include_artifact_content=True
    )
    model_name = project.default_model or "deepseek-chat"
    provider = ModelRouter.get_provider(model_name)
    response = await provider.generate(
        prompt=(
            f"Question: {data.question}\n\n"
            "Project context (bounded JSON):\n"
            f"{json.dumps(context, default=str, ensure_ascii=True)}"
        ),
        system_prompt=(
            "You are the technical lead for this software project. Answer only "
            "from the supplied project context. Clearly distinguish verified "
            "facts, failures, pending approvals, and unknowns. Cite instruction "
            "IDs, commit hashes, artifact titles, or evidence hashes when useful."
        ),
        model=model_name,
    )
    answer = (
        response.content
        if isinstance(response.content, str)
        else json.dumps(response.content, ensure_ascii=False)
    )
    sources = [
        *[f"instruction:{item['id']}" for item in context["instructions"][:10]],
        *[
            f"artifact:{item['title']}"
            for item in context["artifacts"][:10]
        ],
        *[
            f"commit:{item['hash']}"
            for item in context["commits"][:10]
        ],
    ]
    interaction = TechLeadInteraction(
        project_id=project.id,
        user_id=current_user.id,
        question=data.question,
        answer=answer,
        model_name=response.model or model_name,
        sources=sources,
        total_tokens=response.total_tokens,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return {
        "id": interaction.id,
        "answer": answer,
        "model_name": interaction.model_name,
        "sources": sources,
        "total_tokens": interaction.total_tokens,
        "created_at": interaction.created_at.isoformat(),
    }


@router.get("/projects/{project_id}/tech-lead/history")
async def list_tech_lead_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List recent audited technical-lead interactions."""
    await _owned_project(project_id, current_user, db)
    interactions = await db.scalars(
        select(TechLeadInteraction)
        .where(
            TechLeadInteraction.project_id == project_id,
            TechLeadInteraction.user_id == current_user.id,
        )
        .order_by(TechLeadInteraction.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": item.id,
            "question": item.question,
            "answer": item.answer,
            "model_name": item.model_name,
            "sources": item.sources,
            "total_tokens": item.total_tokens,
            "created_at": item.created_at.isoformat(),
        }
        for item in interactions.all()
    ]
