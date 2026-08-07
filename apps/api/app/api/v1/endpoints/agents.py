"""Agent Template and Project Agent API Endpoints."""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.agent_template_repo import AgentTemplateRepository

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────

class AgentTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    capability: str = "reasoning"
    system_prompt: str | None = None
    tools: List[str] | None = None


class AgentTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    capability: str | None = None
    system_prompt: str | None = None
    tools: List[str] | None = None


class AgentTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    capability: str
    system_prompt: str | None = None
    tools: list
    version: int
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None


class AgentVersionResponse(BaseModel):
    id: str
    template_id: str
    version: int
    snapshot: dict
    created_at: str | None = None


class ProjectAgentUpsert(BaseModel):
    template_id: str
    enabled: bool = True
    sort_order: int = 0
    custom_config: dict | None = None


class ProjectAgentResponse(BaseModel):
    id: str
    project_id: str
    template_id: str
    template_name: str = ""
    enabled: bool
    sort_order: int
    custom_config: dict | None = None


def _to_template_response(t) -> AgentTemplateResponse:
    return AgentTemplateResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        capability=t.capability,
        system_prompt=t.system_prompt,
        tools=t.tools or [],
        version=t.version,
        is_active=t.is_active,
        created_at=t.created_at.isoformat() if t.created_at else None,
        updated_at=t.updated_at.isoformat() if t.updated_at else None,
    )


# ── Agent Template Endpoints ──────────────────────────────────────────────

@router.get("/agents", response_model=List[AgentTemplateResponse])
async def list_agents(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all agent templates."""
    repo = AgentTemplateRepository(db)
    templates = await repo.list_all()
    if active_only:
        templates = [t for t in templates if t.is_active]
    return [_to_template_response(t) for t in templates]


@router.post("/agents", response_model=AgentTemplateResponse)
async def create_agent(
    data: AgentTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new agent template."""
    repo = AgentTemplateRepository(db)
    template = await repo.create(
        name=data.name,
        description=data.description,
        capability=data.capability,
        system_prompt=data.system_prompt,
        tools=data.tools,
    )
    return _to_template_response(template)


@router.get("/agents/{agent_id}", response_model=AgentTemplateResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a single agent template."""
    repo = AgentTemplateRepository(db)
    template = await repo.get_by_id(agent_id)
    if not template:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_template_response(template)


@router.patch("/agents/{agent_id}", response_model=AgentTemplateResponse)
async def update_agent(
    agent_id: str,
    data: AgentTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an agent template (bumps version on change)."""
    repo = AgentTemplateRepository(db)
    template = await repo.update(
        template_id=agent_id,
        name=data.name,
        description=data.description,
        capability=data.capability,
        system_prompt=data.system_prompt,
        tools=data.tools,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_template_response(template)


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete an agent template."""
    repo = AgentTemplateRepository(db)
    deleted = await repo.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True}


# ── Agent Version Endpoints ──────────────────────────────────────────────

@router.get("/agents/{agent_id}/versions", response_model=List[AgentVersionResponse])
async def list_agent_versions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List version history for an agent template."""
    repo = AgentTemplateRepository(db)
    template = await repo.get_by_id(agent_id)
    if not template:
        raise HTTPException(status_code=404, detail="Agent not found")
    versions = await repo.list_versions(agent_id)
    return [
        AgentVersionResponse(
            id=v.id,
            template_id=v.template_id,
            version=v.version,
            snapshot=v.snapshot,
            created_at=v.created_at.isoformat() if v.created_at else None,
        )
        for v in versions
    ]


@router.get("/agents/{agent_id}/versions/{version}", response_model=AgentVersionResponse)
async def get_agent_version(
    agent_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific version snapshot."""
    repo = AgentTemplateRepository(db)
    v = await repo.get_version(agent_id, version)
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return AgentVersionResponse(
        id=v.id,
        template_id=v.template_id,
        version=v.version,
        snapshot=v.snapshot,
        created_at=v.created_at.isoformat() if v.created_at else None,
    )


# ── Per-Project Agent Endpoints ───────────────────────────────────────────

@router.get(
    "/projects/{project_id}/agents", response_model=List[ProjectAgentResponse]
)
async def list_project_agents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List agents configured for a specific project."""
    repo = AgentTemplateRepository(db)
    templates = await repo.list_all()
    project_agents = await repo.list_project_agents(project_id)
    pa_map = {pa.template_id: pa for pa in project_agents}

    result = []
    for t in templates:
        pa = pa_map.get(t.id)
        result.append(
            ProjectAgentResponse(
                id=pa.id if pa else "",
                project_id=project_id,
                template_id=t.id,
                template_name=t.name,
                enabled=pa.enabled if pa else True,
                sort_order=pa.sort_order if pa else 0,
                custom_config=pa.custom_config if pa else None,
            )
        )
    return result


@router.post("/projects/{project_id}/agents", response_model=ProjectAgentResponse)
async def configure_project_agent(
    project_id: str,
    data: ProjectAgentUpsert,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Add or update an agent configuration for a project."""
    repo = AgentTemplateRepository(db)
    template = await repo.get_by_id(data.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Agent template not found")
    pa = await repo.upsert_project_agent(
        project_id=project_id,
        template_id=data.template_id,
        enabled=data.enabled,
        sort_order=data.sort_order,
        custom_config=data.custom_config,
    )
    return ProjectAgentResponse(
        id=pa.id,
        project_id=pa.project_id,
        template_id=pa.template_id,
        template_name=template.name,
        enabled=pa.enabled,
        sort_order=pa.sort_order,
        custom_config=pa.custom_config,
    )


@router.delete("/projects/{project_id}/agents/{template_id}")
async def remove_project_agent(
    project_id: str,
    template_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Remove an agent from a project."""
    repo = AgentTemplateRepository(db)
    removed = await repo.remove_project_agent(project_id, template_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Project agent not found")
    return {"ok": True}
