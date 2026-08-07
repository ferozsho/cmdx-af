"""Projects and Workspaces API Endpoints."""

import uuid
from typing import Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.tools.gateway.tool_gateway import ToolGateway

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


class RagQueryRequest(BaseModel):
    """Schema for RAG search query."""

    query: str
    top_k: int = 5


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


@router.get("/projects/{project_id}/tree")
async def get_project_tree(project_id: str) -> Any:
    """Fetch real project file tree from connected Local Agent."""
    tool_res = await ToolGateway.invoke_tool(
        device_id="dev_feroz_pc",
        workspace_id=project_id,
        job_id="job_tree",
        tool_name="get_project_tree",
        arguments={},
    )
    if not tool_res.success:
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/files/content")
async def read_project_file(project_id: str, path: str = Query(...)) -> Any:
    """Read real project file content from connected Local Agent."""
    tool_res = await ToolGateway.invoke_tool(
        device_id="dev_feroz_pc",
        workspace_id=project_id,
        job_id="job_read_file",
        tool_name="read_file",
        arguments={"path": path},
    )
    if not tool_res.success:
        raise HTTPException(status_code=500, detail=tool_res.error)
    return {"path": path, "content": tool_res.result}


@router.post("/projects/{project_id}/rag/search")
async def rag_search_project(project_id: str, data: RagQueryRequest) -> Any:
    """Perform real semantic search via Local Agent RAG Indexer."""
    tool_res = await ToolGateway.invoke_tool(
        device_id="dev_feroz_pc",
        workspace_id=project_id,
        job_id="job_rag",
        tool_name="rag_search",
        arguments={"query": data.query, "top_k": data.top_k},
    )
    if not tool_res.success:
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/git/status")
async def get_git_status(project_id: str) -> Any:
    """Get real Git status from Local Agent workspace."""
    tool_res = await ToolGateway.invoke_tool(
        device_id="dev_feroz_pc",
        workspace_id=project_id,
        job_id="job_git",
        tool_name="git_status",
        arguments={},
    )
    if not tool_res.success:
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result
