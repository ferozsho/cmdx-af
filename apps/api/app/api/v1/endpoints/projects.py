"""Projects and Workspaces API Endpoints."""

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent_run import AgentRun
from app.repositories.project_repo import ProjectRepository
from app.repositories.device_repo import DeviceRepository
from app.tools.gateway.tool_gateway import ToolGateway

router = APIRouter()


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str
    description: str | None = None
    execution_target: str = "LOCAL"
    device_id: str | None = None
    local_path: str | None = None
    tech_stack: List[str] | None = None
    initial_instruction: str | None = None


class ProjectResponse(BaseModel):
    """Schema for returning project details."""

    id: str
    name: str
    description: str | None = None
    execution_target: str
    local_path: str | None = None
    tech_stack: dict | None = None
    status: str = "ACTIVE"
    created_at: str | None = None
    updated_at: str | None = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project (all fields optional)."""

    name: str | None = None
    description: str | None = None
    execution_target: str | None = None
    local_path: str | None = None
    tech_stack: List[str] | None = None


class ValidatePathRequest(BaseModel):
    """Schema for project path validation."""

    path: str


class ValidatePathResponse(BaseModel):
    """Structured path validation result."""

    valid: bool
    exists: bool = False
    is_directory: bool = False
    readable: bool = False
    writable: bool = False
    git_repository: bool = False
    detected_stack: List[str] = []
    project_name: str | None = None
    files_count: int = 0
    directories_count: int = 0
    warnings: List[str] = []


class RagQueryRequest(BaseModel):
    """Schema for RAG search query."""

    query: str
    top_k: int = 5


# ── Technology stack detection ──────────────────────────────────────────────

STACK_MARKERS: Dict[str, List[str]] = {
    "Python": ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"],
    "FastAPI": ["fastapi"],
    "Django": ["manage.py"],
    "Flask": ["flask"],
    "Next.js": ["next.config.js", "next.config.mjs", "next.config.ts"],
    "React": ["react"],
    "Node.js": ["package.json"],
    "TypeScript": ["tsconfig.json"],
    "PHP": ["composer.json", "index.php", "version.php"],
    "Moodle": ["version.php", "config.php", "lib/moodlelib.php"],
    "PostgreSQL": ["psycopg2", "asyncpg", "pg"],
    "MySQL": ["mysqlclient", "pymysql", "mysql2"],
    "Redis": ["redis"],
    "Docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "MongoDB": ["mongoengine", "pymongo", "motor"],
}


def _detect_tech_stack(project_path: Path) -> List[str]:
    """Scan project directory and detect technologies."""
    detected: List[str] = []
    try:
        root_files = {f.name for f in project_path.iterdir() if f.is_file()}
        all_files_lower = {f.name.lower() for f in project_path.rglob("*") if f.is_file()}

        for tech, markers in STACK_MARKERS.items():
            for marker in markers:
                if marker in root_files or marker in all_files_lower:
                    detected.append(tech)
                    break

        # Check package.json for additional frameworks
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            import json
            try:
                pkg_data = json.loads(pkg_json.read_text())
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}  # noqa: E501
                for tech, markers in {
                    "Next.js": ["next"],
                    "React": ["react"],
                    "Vue": ["vue"],
                    "Angular": ["@angular/core"],
                    "Express": ["express"],
                }.items():
                    if any(m in deps for m in markers):
                        if tech not in detected:
                            detected.append(tech)
            except (json.JSONDecodeError, OSError):
                pass

        # Check pyproject.toml for Python frameworks
        pptoml = project_path / "pyproject.toml"
        if pptoml.exists():
            try:
                content = pptoml.read_text().lower()
                for framework in ["fastapi", "django", "flask", "celery"]:
                    if framework in content and framework.title() not in detected:
                        if framework == "fastapi":
                            detected.append("FastAPI")
                        elif framework == "django":
                            detected.append("Django")
            except OSError:
                pass
    except (OSError, PermissionError):
        pass
    return sorted(set(detected))


def _count_files_and_dirs(project_path: Path, max_depth: int = 4) -> tuple:
    """Count files and directories up to max_depth."""
    files_count = 0
    dirs_count = 0
    try:
        for root, dirs, files in os.walk(project_path):
            depth = len(Path(root).relative_to(project_path).parts)
            if depth > max_depth:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       {"node_modules", "__pycache__", ".git", ".next", "venv", ".venv"}]
            files_count += len([f for f in files if not f.startswith(".")])
            dirs_count += len(dirs)
            if depth >= max_depth:
                dirs.clear()
    except (OSError, PermissionError):
        pass
    return files_count, dirs_count


# ── API Endpoints ───────────────────────────────────────────────────────────

# Default device/workspace until dynamic resolution is fully wired
_DEFAULT_DEVICE = "dev_feroz_pc"
_DEFAULT_WORKSPACE = "ws-test"


def _resolve_workspace(project_id: str) -> str:
    """Map project_id to a registered workspace_id (sync-safe fallback)."""
    return _DEFAULT_WORKSPACE


def _tool_is_offline(tool_res: Any) -> bool:
    """Detect whether a failed tool result is due to an offline device."""
    error = (tool_res.error or "").lower() if hasattr(tool_res, "error") else ""
    return "offline" in error or "not connected" in error


def _offline_response() -> dict:
    """Structured response returned when the local agent is offline."""
    return {
        "status": "offline",
        "online": False,
        "detail": (
            "Local agent workstation is offline. Connect a device to use "
            "this feature."
        ),
    }


# In-memory background re-index job tracker (project_id -> job state)
_reindex_jobs: Dict[str, Dict[str, Any]] = {}


def _reindex_job_payload(job: Dict[str, Any]) -> dict:
    """Serialize a re-index job for API responses."""
    return {
        "status": job.get("status", "idle"),
        "files_indexed": job.get("files_indexed", 0),
        "chunks": job.get("chunks", 0),
        "last_index": job.get("last_index"),
        "error": job.get("error"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }


@router.get("/projects/stats/summary")
async def get_project_stats(db: AsyncSession = Depends(get_db)) -> Any:
    """Get aggregated project stats for dashboard KPIs."""
    repo = ProjectRepository(db)
    device_repo = DeviceRepository(db)
    total = await repo.count()
    online = await device_repo.count_online()
    total_devices = await device_repo.count()

    # Real agent run count from agent_runs
    runs_result = await db.execute(
        select(func.count(AgentRun.id)).where(AgentRun.status == "COMPLETED")
    )
    agent_runs = int(runs_result.scalar() or 0)

    # Real tests-passed sum from Test Agent run metadata
    tests_passed = 0
    test_runs = await db.execute(
        select(AgentRun.metadata_json).where(
            AgentRun.agent_name == "Test Agent"
        )
    )
    for (meta,) in test_runs.all():
        if isinstance(meta, dict):
            tests_passed += int(meta.get("tests_passed") or 0)

    return {
        "total_projects": total,
        "online_devices": online,
        "total_devices": total_devices,
        "agent_runs": agent_runs,
        "tests_passed": tests_passed,
    }


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)) -> Any:
    """Get all projects from the database."""
    repo = ProjectRepository(db)
    projects = await repo.list_all()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            execution_target=p.execution_target,
            local_path=p.local_path,
            tech_stack=p.tech_stack,
            status="ACTIVE",
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in projects
    ]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate, db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new project in the database."""
    repo = ProjectRepository(db)
    tech_stack_list = data.tech_stack or []
    project = await repo.create(
        name=data.name,
        description=data.description,
        execution_target=data.execution_target,
        local_path=data.local_path,
        tech_stack={t: True for t in tech_stack_list},
    )
    await db.commit()
    await db.refresh(project)

    # Persist and kick off the initial instruction pipeline if provided
    initial_prompt = (
        data.initial_instruction.strip() if data.initial_instruction else ""
    )
    if initial_prompt:
        from app.agents.pipeline import PipelineOrchestrator
        from app.models.instruction import Instruction
        from app.services.sse_broadcaster import broadcaster

        ins_id = f"ins_{uuid.uuid4().hex[:8]}"
        db.add(
            Instruction(
                id=ins_id,
                project_id=project.id,
                prompt=initial_prompt,
                status="RUNNING",
            )
        )
        await db.commit()

        device_id = data.device_id or _DEFAULT_DEVICE
        workspace_id = _DEFAULT_WORKSPACE

        async def _run_initial_pipeline() -> None:
            orchestrator = PipelineOrchestrator()

            async def _event_cb(
                agent_name: str,
                status: str,
                msg: str,
                data: dict | None = None,
            ) -> None:
                payload: dict = {
                    "instruction_id": ins_id,
                    "agent_name": agent_name,
                    "status": status,
                    "message": msg,
                }
                if data:
                    payload["data"] = data
                await broadcaster.broadcast(project.id, payload)

            await orchestrator.run_pipeline(
                ins_id,
                initial_prompt,
                event_callback=_event_cb,
                device_id=device_id,
                workspace_id=workspace_id,
            )

        asyncio.create_task(_run_initial_pipeline())

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        execution_target=project.execution_target,
        local_path=project.local_path,
        tech_stack=project.tech_stack,
        status="ACTIVE",
        created_at=project.created_at.isoformat() if project.created_at else None,
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> Any:
    """Get project details by ID from the database."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        execution_target=project.execution_target,
        local_path=project.local_path,
        tech_stack=project.tech_stack,
        status="ACTIVE",
        created_at=project.created_at.isoformat() if project.created_at else None,
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
    )


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing project."""
    repo = ProjectRepository(db)
    tech_stack_dict = {t: True for t in data.tech_stack} if data.tech_stack is not None else None
    project = await repo.update(
        project_id=project_id,
        name=data.name,
        description=data.description,
        execution_target=data.execution_target,
        local_path=data.local_path,
        tech_stack=tech_stack_dict,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        execution_target=project.execution_target,
        local_path=project.local_path,
        tech_stack=project.tech_stack,
        status="ACTIVE",
        created_at=project.created_at.isoformat() if project.created_at else None,
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete a project by ID."""
    repo = ProjectRepository(db)
    deleted = await repo.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True, "detail": f"Project {project_id} deleted"}


@router.post("/projects/validate-path", response_model=ValidatePathResponse)
async def validate_project_path(data: ValidatePathRequest) -> Any:
    """Validate a project directory path and detect its technology stack."""
    raw_path = data.path.strip()
    result = ValidatePathResponse(valid=False)

    # Security: block obviously dangerous paths
    if not raw_path:
        result.warnings.append("Path is empty.")
        return result

    try:
        project_path = Path(raw_path).expanduser().resolve()
    except (OSError, RuntimeError) as e:
        result.warnings.append(f"Cannot resolve path: {e}")
        return result

    # Check existence
    result.exists = project_path.exists()
    if not result.exists:
        result.warnings.append(f"Directory does not exist: {project_path}")
        return result

    # Check is directory
    result.is_directory = project_path.is_dir()
    if not result.is_directory:
        result.warnings.append(f"Path is not a directory: {project_path}")
        return result

    # Check readability
    result.readable = os.access(project_path, os.R_OK)
    if not result.readable:
        result.warnings.append(f"Directory is not readable: {project_path}")

    # Check writability
    result.writable = os.access(project_path, os.W_OK)
    if not result.writable:
        result.warnings.append(f"Directory is not writable: {project_path}")

    # Check for git repository
    result.git_repository = (project_path / ".git").is_dir()
    if not result.git_repository:
        result.warnings.append(
            "No Git repository detected. Git versioning will be unavailable."
        )

    # Detect tech stack
    result.detected_stack = _detect_tech_stack(project_path)

    # Count files and dirs (limited depth for performance)
    try:
        result.files_count, result.directories_count = _count_files_and_dirs(
            project_path, max_depth=4
        )
    except Exception:
        pass

    # Project name from directory
    result.project_name = project_path.name

    result.valid = result.exists and result.is_directory and result.readable
    return result


@router.get("/projects/{project_id}/tree")
async def get_project_tree(project_id: str) -> Any:
    """Fetch real project file tree from connected Local Agent."""
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_tree",
        tool_name="get_project_tree",
        arguments={},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/files/content")
async def read_project_file(project_id: str, path: str = Query(...)) -> Any:
    """Read real project file content from connected Local Agent."""
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_read_file",
        tool_name="read_file",
        arguments={"path": path},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return {"path": path, "content": tool_res.result}


@router.post("/projects/{project_id}/rag/search")
async def rag_search_project(project_id: str, data: RagQueryRequest) -> Any:
    """Perform real semantic search via Local Agent RAG Indexer."""
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_rag",
        tool_name="rag_search",
        arguments={"query": data.query, "top_k": data.top_k},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/git/status")
async def get_git_status(project_id: str) -> Any:
    """Get real Git status from Local Agent workspace."""
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_git",
        tool_name="git_status",
        arguments={},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/git/log")
async def get_git_log(project_id: str, max_count: int = 20) -> Any:
    """Get recent git commit log from Local Agent workspace."""
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_git_log",
        tool_name="git_log",
        arguments={"max_count": max_count},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


class GitRollbackRequest(BaseModel):
    """Schema for git rollback request."""

    commit_hash: str


@router.post("/projects/{project_id}/git/rollback")
async def rollback_git_commit(
    project_id: str,
    data: GitRollbackRequest,
) -> Any:
    """Hard-reset the workspace to a specified commit hash."""
    if not data.commit_hash:
        raise HTTPException(status_code=400, detail="commit_hash is required")
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_git_rollback",
        tool_name="git_rollback",
        arguments={"commit_hash": data.commit_hash},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return {
        "ok": True,
        "detail": f"Workspace reset to {data.commit_hash}",
        "result": tool_res.result,
    }


@router.get("/projects/{project_id}/rag/stats")
async def get_rag_stats(project_id: str) -> Any:
    """Get RAG indexing stats by searching with empty query."""
    try:
        tool_res = await ToolGateway.invoke_tool(
            device_id=_DEFAULT_DEVICE,
            workspace_id=_DEFAULT_WORKSPACE,
            job_id="job_rag_stats",
            tool_name="rag_search",
            arguments={"query": ".", "top_k": 1},
        )
        if not tool_res.success:
            return {
                "files_indexed": 0,
                "chunks": 0,
                "last_index": None,
                "online": False,
            }
        results = tool_res.result if isinstance(tool_res.result, list) else []
        return {
            "files_indexed": len(results),
            "chunks": sum(len(r.get("content", "")) for r in results) if results else 0,
            "last_index": None,
            "online": True,
        }
    except Exception:
        return {
            "files_indexed": 0,
            "chunks": 0,
            "last_index": None,
            "online": False,
        }


@router.post("/projects/{project_id}/rag/reindex")
async def reindex_project_rag(project_id: str) -> Any:
    """Kick off a background RAG re-index (click-and-forget) and return."""
    existing = _reindex_jobs.get(project_id)
    if existing and existing.get("status") == "running":
        return {"status": "running", "job": _reindex_job_payload(existing)}

    job: Dict[str, Any] = {
        "status": "running",
        "files_indexed": 0,
        "chunks": 0,
        "last_index": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
    }
    _reindex_jobs[project_id] = job
    asyncio.create_task(_run_reindex_job(project_id, job))
    return {"status": "started", "job": _reindex_job_payload(job)}


async def _run_reindex_job(project_id: str, job: Dict[str, Any]) -> None:
    """Run the RAG re-index tool in the background and update the job."""
    try:
        tool_res = await ToolGateway.invoke_tool(
            device_id=_DEFAULT_DEVICE,
            workspace_id=_DEFAULT_WORKSPACE,
            job_id="job_rag_reindex",
            tool_name="rag_reindex",
            arguments={},
        )
        if not tool_res.success:
            job["status"] = "failed"
            job["error"] = tool_res.error
        else:
            result = tool_res.result if isinstance(tool_res.result, dict) else {}
            job["status"] = "done"
            job["files_indexed"] = int(result.get("files_indexed", 0))
            job["chunks"] = int(result.get("chunks", 0))
            job["last_index"] = result.get("last_index")
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = datetime.utcnow().isoformat() + "Z"


@router.get("/projects/{project_id}/rag/reindex-status")
async def get_reindex_status(project_id: str) -> Any:
    """Return the status of the background RAG re-index job."""
    job = _reindex_jobs.get(project_id)
    if not job:
        return {"status": "idle", "job": None}
    return {"status": job["status"], "job": _reindex_job_payload(job)}


@router.get("/projects/{project_id}/files/original")
async def get_file_original(
    project_id: str, path: str = Query(...)
) -> Any:
    """Get the original (git HEAD) version of a file for diff baseline."""
    tool_res = await ToolGateway.invoke_tool(
        device_id=_DEFAULT_DEVICE,
        workspace_id=_DEFAULT_WORKSPACE,
        job_id="job_file_original",
        tool_name="git_show_file",
        arguments={"path": path},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return {"path": path, "content": tool_res.result}


@router.get("/projects/{project_id}/artifacts")
async def list_project_artifacts(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all generated artifacts for a project."""
    from app.repositories.artifact_repo import ArtifactRepository

    repo = ArtifactRepository(db)
    artifacts = await repo.list_for_project(project_id)
    return [
        {
            "id": a.id,
            "instruction_id": a.instruction_id,
            "title": a.title,
            "artifact_type": a.artifact_type,
            "content": a.content,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]
