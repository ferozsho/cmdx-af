"""Projects and Workspaces API Endpoints."""

import uuid
from typing import Any, List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str
    description: str | None = None
    execution_target: str = "LOCAL"
    device_id: str | None = None
    local_path: str | None = None


class ProjectResponse(BaseModel):
    """Schema for returning project details."""

    id: str
    name: str
    description: str | None = None
    execution_target: str
    status: str = "ACTIVE"


MOCK_PROJECTS = [
    {
        "id": "prj_demo_001",
        "name": "Commerce Platform",
        "description": "Full-stack E-commerce analytics & payment platform",
        "execution_target": "LOCAL",
        "status": "ACTIVE",
    }
]


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects() -> Any:
    """Get all projects."""
    return MOCK_PROJECTS


@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate) -> Any:
    """Create new project."""
    new_proj = {
        "id": f"prj_{uuid.uuid4().hex[:8]}",
        "name": data.name,
        "description": data.description,
        "execution_target": data.execution_target,
        "status": "ACTIVE",
    }
    MOCK_PROJECTS.append(new_proj)
    return new_proj


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> Any:
    """Get project details by ID."""
    for p in MOCK_PROJECTS:
        if p["id"] == project_id:
            return p
    return MOCK_PROJECTS[0]
