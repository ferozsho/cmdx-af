"""Projects and Workspaces API Endpoints."""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.policies import check_fs_policy, check_git_policy
from app.core.security import get_current_user
from app.models.agent_run import AgentRun
from app.models.background_job import BackgroundJob
from app.models.device import Device
from app.models.git_commit import GitCommit
from app.models.instruction import Instruction
from app.models.project import Project
from app.models.user import User
from app.models.verification_run import VerificationRun
from app.models.workspace import Workspace
from app.repositories.device_repo import DeviceRepository
from app.repositories.project_repo import ProjectRepository
from app.services.approvals import ApprovalRequiredError, authorize_tool
from app.services.instruction_events import append_instruction_event
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
    # Git authorization
    git_enabled: bool = True
    git_branch_patterns: List[str] | None = None
    git_require_pr: bool = False
    ci_gate_enabled: bool = True
    git_commit_template: str | None = None
    # Filesystem access
    fs_read_enabled: bool = True
    fs_write_enabled: bool = True
    fs_delete_enabled: bool = True
    approval_mode: Literal["NEVER", "RISKY", "ALWAYS"] = "RISKY"
    command_allowlist: List[str] | None = None
    max_command_seconds: int = 120
    default_model: str | None = None


class ProjectResponse(BaseModel):
    """Schema for returning project details."""

    id: str
    name: str
    description: str | None = None
    execution_target: str
    local_path: str | None = None
    tech_stack: dict | None = None
    default_model: str | None = None
    status: str = "ACTIVE"
    created_at: str | None = None
    updated_at: str | None = None
    # Git authorization
    git_enabled: bool = True
    git_branch_patterns: list | None = None
    git_require_pr: bool = False
    ci_gate_enabled: bool = True
    git_commit_template: str | None = None
    # Filesystem access
    fs_read_enabled: bool = True
    fs_write_enabled: bool = True
    fs_delete_enabled: bool = True
    approval_mode: str = "RISKY"
    command_allowlist: list[str] | None = None
    max_command_seconds: int = 120


class ProjectUpdate(BaseModel):
    """Schema for updating a project (all fields optional)."""

    name: str | None = None
    description: str | None = None
    execution_target: str | None = None
    local_path: str | None = None
    tech_stack: List[str] | None = None
    # Git authorization
    git_enabled: bool | None = None
    git_branch_patterns: List[str] | None = None
    git_require_pr: bool | None = None
    ci_gate_enabled: bool | None = None
    git_commit_template: str | None = None
    # Filesystem access
    fs_read_enabled: bool | None = None
    fs_write_enabled: bool | None = None
    fs_delete_enabled: bool | None = None
    approval_mode: Literal["NEVER", "RISKY", "ALWAYS"] | None = None
    command_allowlist: List[str] | None = None
    max_command_seconds: int | None = None
    default_model: str | None = None


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

_DEFAULT_WORKSPACE = "ws-test"


async def _require_project(
    project_id: str,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Return an owned project without revealing other users' IDs."""
    project = await ProjectRepository(db).get_by_id(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _resolve_user_device(
    user_id: str,
    db: AsyncSession,
    preferred_device_id: str | None = None,
) -> str | None:
    """Resolve a device owned by the user, optionally requiring a preferred ID."""
    repo = DeviceRepository(db)
    if preferred_device_id:
        device = await repo.get_by_id(preferred_device_id)
        if not device or device.user_id != user_id:
            raise HTTPException(status_code=404, detail="Device not found")
        return device.id
    devices = await repo.list_for_user(user_id)
    return devices[0].id if devices else None


async def _resolve_execution_target(
    project: Project,
    db: AsyncSession,
) -> tuple[str, str]:
    """Resolve an owned device and workspace used for project tool calls.

    Priority: project.local_path (the folder set on the project) → a
    workspace registered in the DB for this project → the default workspace.
    A workspace is only accepted when its device belongs to the project owner.
    """
    result = await db.execute(
        select(Workspace)
        .join(Device, Device.id == Workspace.device_id)
        .where(
            Workspace.project_id == project.id,
            Device.user_id == project.user_id,
        )
        .limit(1)
    )
    workspace = result.scalar_one_or_none()
    if workspace:
        return workspace.device_id, workspace.id

    device_id = await _resolve_user_device(project.user_id, db)
    return device_id or "", _DEFAULT_WORKSPACE


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


def _reindex_job_payload(job: BackgroundJob) -> dict:
    """Serialize a re-index job for API responses."""
    result = job.result_data or {}
    public_status = {
        "PENDING": "running",
        "RUNNING": "running",
        "COMPLETED": "done",
        "FAILED": "failed",
    }.get(job.status, job.status.lower())
    return {
        "id": job.id,
        "status": public_status,
        "files_indexed": int(result.get("files_indexed") or 0),
        "chunks": int(result.get("chunks") or 0),
        "last_index": result.get("last_index"),
        "error": job.last_error,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": (
            job.finished_at.isoformat() if job.finished_at else None
        ),
    }


@router.get("/projects/stats/summary")
async def get_project_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get aggregated project stats for dashboard KPIs."""
    repo = ProjectRepository(db)
    device_repo = DeviceRepository(db)
    total = await repo.count_for_user(current_user.id)
    online = await device_repo.count_online_for_user(current_user.id)
    total_devices = await device_repo.count_for_user(current_user.id)

    # Real agent run count from agent_runs
    runs_result = await db.execute(
        select(func.count(AgentRun.id))
        .join(Instruction, Instruction.id == AgentRun.instruction_id)
        .join(Project, Project.id == Instruction.project_id)
        .where(
            AgentRun.status == "COMPLETED",
            Project.user_id == current_user.id,
        )
    )
    agent_runs = int(runs_result.scalar() or 0)

    # Real tests-passed sum from Test Agent run metadata
    tests_passed = 0
    test_runs = await db.execute(
        select(AgentRun.metadata_json)
        .join(Instruction, Instruction.id == AgentRun.instruction_id)
        .join(Project, Project.id == Instruction.project_id)
        .where(
            AgentRun.agent_name == "Test Agent",
            Project.user_id == current_user.id,
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
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get all projects for the authenticated user."""
    repo = ProjectRepository(db)
    projects = await repo.list_for_user(current_user.id)
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
            git_enabled=bool(p.git_enabled),
            git_branch_patterns=p.git_branch_patterns if p.git_branch_patterns else None,
            git_require_pr=bool(p.git_require_pr),
            ci_gate_enabled=bool(p.ci_gate_enabled),
            git_commit_template=p.git_commit_template,
            fs_read_enabled=bool(p.fs_read_enabled),
            fs_write_enabled=bool(p.fs_write_enabled),
            fs_delete_enabled=bool(p.fs_delete_enabled),
            approval_mode=p.approval_mode,
            command_allowlist=p.command_allowlist,
            max_command_seconds=p.max_command_seconds,
            default_model=p.default_model,
        )
        for p in projects
    ]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a new project in the database."""
    repo = ProjectRepository(db)
    initial_prompt = (
        data.initial_instruction.strip() if data.initial_instruction else ""
    )
    await _resolve_user_device(
        current_user.id,
        db,
        data.device_id,
    )
    tech_stack_list = data.tech_stack or []
    project = await repo.create(
        name=data.name,
        description=data.description,
        execution_target=data.execution_target,
        local_path=data.local_path,
        tech_stack={t: True for t in tech_stack_list},
        user_id=current_user.id,
        git_enabled=data.git_enabled,
        git_branch_patterns=data.git_branch_patterns,
        git_require_pr=data.git_require_pr,
        ci_gate_enabled=data.ci_gate_enabled,
        git_commit_template=data.git_commit_template,
        fs_read_enabled=data.fs_read_enabled,
        fs_write_enabled=data.fs_write_enabled,
        fs_delete_enabled=data.fs_delete_enabled,
        approval_mode=data.approval_mode,
        command_allowlist=data.command_allowlist,
        max_command_seconds=data.max_command_seconds,
        default_model=data.default_model,
    )
    await db.commit()
    await db.refresh(project)

    # Persist the initial instruction for the durable worker if provided.
    if initial_prompt:
        ins_id = f"ins_{uuid.uuid4().hex[:8]}"
        db.add(
            Instruction(
                id=ins_id,
                project_id=project.id,
                user_id=current_user.id,
                prompt=initial_prompt,
                status="PENDING",
            )
        )
        await append_instruction_event(
            project.id,
            ins_id,
            {
                "instruction_id": ins_id,
                "agent_name": "System",
                "status": "PENDING",
                "message": "Instruction queued for execution.",
            },
            db,
        )
        await db.commit()

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
        git_enabled=bool(project.git_enabled),
        git_branch_patterns=project.git_branch_patterns if project.git_branch_patterns else None,
        git_require_pr=bool(project.git_require_pr),
        ci_gate_enabled=bool(project.ci_gate_enabled),
        git_commit_template=project.git_commit_template,
        fs_read_enabled=bool(project.fs_read_enabled),
        fs_write_enabled=bool(project.fs_write_enabled),
        fs_delete_enabled=bool(project.fs_delete_enabled),
        approval_mode=project.approval_mode,
        command_allowlist=project.command_allowlist,
        max_command_seconds=project.max_command_seconds,
        default_model=project.default_model,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get project details by ID from the database."""
    project = await _require_project(project_id, current_user, db)
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
        git_enabled=bool(project.git_enabled),
        git_branch_patterns=project.git_branch_patterns if project.git_branch_patterns else None,
        git_require_pr=bool(project.git_require_pr),
        ci_gate_enabled=bool(project.ci_gate_enabled),
        git_commit_template=project.git_commit_template,
        fs_read_enabled=bool(project.fs_read_enabled),
        fs_write_enabled=bool(project.fs_write_enabled),
        fs_delete_enabled=bool(project.fs_delete_enabled),
        approval_mode=project.approval_mode,
        command_allowlist=project.command_allowlist,
        max_command_seconds=project.max_command_seconds,
        default_model=project.default_model,
    )


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update an existing project."""
    repo = ProjectRepository(db)
    if not await repo.belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    tech_stack_dict = {t: True for t in data.tech_stack} if data.tech_stack is not None else None
    project = await repo.update(
        project_id=project_id,
        name=data.name,
        description=data.description,
        execution_target=data.execution_target,
        local_path=data.local_path,
        tech_stack=tech_stack_dict,
        git_enabled=data.git_enabled,
        git_branch_patterns=data.git_branch_patterns,
        git_require_pr=data.git_require_pr,
        ci_gate_enabled=data.ci_gate_enabled,
        git_commit_template=data.git_commit_template,
        fs_read_enabled=data.fs_read_enabled,
        fs_write_enabled=data.fs_write_enabled,
        fs_delete_enabled=data.fs_delete_enabled,
        approval_mode=data.approval_mode,
        command_allowlist=data.command_allowlist,
        max_command_seconds=data.max_command_seconds,
        default_model=data.default_model,
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
        git_enabled=bool(project.git_enabled),
        git_branch_patterns=project.git_branch_patterns if project.git_branch_patterns else None,
        git_require_pr=bool(project.git_require_pr),
        ci_gate_enabled=bool(project.ci_gate_enabled),
        git_commit_template=project.git_commit_template,
        fs_read_enabled=bool(project.fs_read_enabled),
        fs_write_enabled=bool(project.fs_write_enabled),
        fs_delete_enabled=bool(project.fs_delete_enabled),
        approval_mode=project.approval_mode,
        command_allowlist=project.command_allowlist,
        max_command_seconds=project.max_command_seconds,
        default_model=project.default_model,
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete a project by ID."""
    repo = ProjectRepository(db)
    if not await repo.belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    deleted = await repo.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True, "detail": f"Project {project_id} deleted"}


@router.post("/projects/validate-path", response_model=ValidatePathResponse)
async def validate_project_path(
    data: ValidatePathRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Validate a project directory path via the connected Local Agent.

    The folder lives on the developer's host machine, so the check is
    delegated to the local agent over WSS (the API container cannot see
    the host filesystem).
    """
    raw_path = data.path.strip()
    if not raw_path:
        return ValidatePathResponse(valid=False, warnings=["Path is empty."])

    device_id = await _resolve_user_device(current_user.id, db)
    if not device_id:
        return ValidatePathResponse(
            valid=False,
            warnings=[
                "No paired workstation is available. Pair a device to "
                "validate folders."
            ],
        )
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=raw_path,
        job_id="job_validate_path",
        tool_name="validate_path",
        arguments={"path": raw_path},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return ValidatePathResponse(
                valid=False,
                warnings=[
                    "Local agent workstation is offline. Connect a device "
                    "to validate folders."
                ],
            )
        return ValidatePathResponse(
            valid=False,
            warnings=[tool_res.error or "Folder validation failed"],
        )

    result = tool_res.result or {}
    return ValidatePathResponse(
        valid=bool(result.get("valid")),
        exists=bool(result.get("exists")),
        is_directory=bool(result.get("is_directory")),
        readable=bool(result.get("readable")),
        writable=bool(result.get("writable")),
        git_repository=bool(result.get("git_repository")),
        detected_stack=result.get("detected_stack") or [],
        project_name=result.get("project_name"),
        files_count=int(result.get("files_count") or 0),
        directories_count=int(result.get("directories_count") or 0),
        warnings=result.get("warnings") or [],
    )


@router.get("/projects/{project_id}/tree")
async def get_project_tree(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Fetch real project file tree from connected Local Agent."""
    project = await _require_project(project_id, current_user, db)
    check_fs_policy(project, "read")
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
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
async def read_project_file(
    project_id: str,
    path: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Read real project file content from connected Local Agent."""
    project = await _require_project(project_id, current_user, db)
    check_fs_policy(project, "read")
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
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
async def rag_search_project(
    project_id: str,
    data: RagQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Perform real semantic search via Local Agent RAG Indexer."""
    project = await _require_project(project_id, current_user, db)
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
        job_id="job_rag",
        tool_name="rag_search",
        arguments={"query": data.query, "top_k": data.top_k},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/rag/chunks")
async def list_rag_chunks(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    q: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Browse the currently indexed RAG chunks (paginated, optional filter).

    Used by the RAG tab's default "All Chunks" view.
    """
    project = await _require_project(project_id, current_user, db)
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
        job_id="job_rag_chunks",
        tool_name="rag_chunks",
        arguments={"offset": offset, "limit": limit, "query": q},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/git/status")
async def get_git_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get real Git status from Local Agent workspace."""
    project = await _require_project(project_id, current_user, db)
    check_git_policy(project, "read")
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
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
async def get_git_log(
    project_id: str,
    max_count: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get recent git commit log from Local Agent workspace."""
    project = await _require_project(project_id, current_user, db)
    check_git_policy(project, "read")
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
        job_id="job_git_log",
        tool_name="git_log",
        arguments={"max_count": max_count},
    )
    if not tool_res.success:
        if _tool_is_offline(tool_res):
            return _offline_response()
        raise HTTPException(status_code=500, detail=tool_res.error)
    return tool_res.result


@router.get("/projects/{project_id}/git/provenance")
async def list_git_provenance(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List durable AI authorship and verification metadata for owned commits."""
    await _require_project(project_id, current_user, db)
    records = await db.scalars(
        select(GitCommit)
        .where(
            GitCommit.project_id == project_id,
            GitCommit.user_id == current_user.id,
        )
        .order_by(GitCommit.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": record.id,
            "instruction_id": record.instruction_id,
            "commit_hash": record.commit_hash,
            "branch": record.branch,
            "message": record.message,
            "ai_generated": record.ai_generated,
            "provenance_digest": record.provenance_digest,
            "prompt_digest": record.prompt_digest,
            "model_name": record.model_name,
            "changed_files": record.changed_files,
            "commit_metadata": record.commit_metadata,
            "verification_status": record.verification_status,
            "created_at": record.created_at.isoformat(),
        }
        for record in records.all()
    ]


@router.get("/projects/{project_id}/verifications")
async def list_verification_runs(
    project_id: str,
    instruction_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List bounded, redacted verification evidence for an owned project."""
    await _require_project(project_id, current_user, db)
    query = select(VerificationRun).where(
        VerificationRun.project_id == project_id
    )
    if instruction_id:
        query = query.where(VerificationRun.instruction_id == instruction_id)
    records = await db.scalars(
        query.order_by(VerificationRun.created_at.desc()).limit(200)
    )
    return [
        {
            "id": record.id,
            "instruction_id": record.instruction_id,
            "category": record.category,
            "executable": record.executable,
            "command_digest": record.command_digest,
            "status": record.status,
            "exit_code": record.exit_code,
            "duration_seconds": record.duration_seconds,
            "output_digest": record.output_digest,
            "output_excerpt": record.output_excerpt,
            "created_at": record.created_at.isoformat(),
        }
        for record in records.all()
    ]


class GitRollbackRequest(BaseModel):
    """Schema for git rollback request."""

    commit_hash: str


@router.post("/projects/{project_id}/git/rollback")
async def rollback_git_commit(
    project_id: str,
    data: GitRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Hard-reset the workspace to a specified commit hash."""
    if not data.commit_hash:
        raise HTTPException(status_code=400, detail="commit_hash is required")
    project = await _require_project(project_id, current_user, db)
    check_git_policy(project, "rollback")
    try:
        authorization_id = await authorize_tool(
            project=project,
            user_id=current_user.id,
            instruction_id=None,
            tool_name="git_rollback",
            operation="git.rollback",
            arguments={"commit_hash": data.commit_hash},
            summary=f"Roll back the workspace to commit {data.commit_hash}.",
        )
    except ApprovalRequiredError as exc:
        return JSONResponse(
            status_code=202,
            content={
                "status": "WAITING_APPROVAL",
                "approval_id": exc.approval_id,
                "detail": exc.summary,
            },
        )
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
        job_id="job_git_rollback",
        tool_name="git_rollback",
        arguments={"commit_hash": data.commit_hash},
        authorization_id=authorization_id,
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
async def get_rag_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get live RAG indexing stats + progress from the Local Agent."""
    project = await _require_project(project_id, current_user, db)
    try:
        device_id, workspace = await _resolve_execution_target(project, db)
        tool_res = await ToolGateway.invoke_tool(
            device_id=device_id,
            workspace_id=workspace,
            job_id="job_rag_stats",
            tool_name="rag_status",
            arguments={},
        )
        if not tool_res.success:
            return {
                "online": False,
                "state": "offline",
                "indexing": False,
                "progress": 0,
                "files_indexed": 0,
                "chunks": 0,
                "last_index": None,
            }
        result = tool_res.result if isinstance(tool_res.result, dict) else {}
        return {
            "online": True,
            "state": result.get("state", "idle"),
            "indexing": bool(result.get("indexing")),
            "progress": float(result.get("progress") or 0),
            "files_scanned": int(result.get("scanned_files") or 0),
            "total_files": int(result.get("total_files") or 0),
            "files_indexed": int(result.get("files_indexed") or 0),
            "chunks": int(result.get("chunks") or 0),
            "last_index": result.get("finished_at"),
            "current_file": result.get("current_file"),
            "started_at": result.get("started_at"),
        }
    except Exception:
        return {
            "online": False,
            "state": "offline",
            "indexing": False,
            "progress": 0,
            "files_indexed": 0,
            "chunks": 0,
            "last_index": None,
        }


@router.post("/projects/{project_id}/rag/reindex")
async def reindex_project_rag(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Durably enqueue a RAG re-index for the worker process."""
    locked_project = await db.scalar(
        select(Project)
        .where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .with_for_update()
    )
    if not locked_project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = await db.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.project_id == project_id,
            BackgroundJob.job_type == "RAG_REINDEX",
            BackgroundJob.status.in_(["PENDING", "RUNNING"]),
        )
        .order_by(BackgroundJob.created_at.desc())
        .limit(1)
    )
    if existing:
        return {"status": "running", "job": _reindex_job_payload(existing)}

    job = BackgroundJob(
        project_id=project_id,
        user_id=current_user.id,
        job_type="RAG_REINDEX",
        status="PENDING",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return {"status": "started", "job": _reindex_job_payload(job)}


@router.get("/projects/{project_id}/rag/reindex-status")
async def get_reindex_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return the status of the background RAG re-index job."""
    await _require_project(project_id, current_user, db)
    job = await db.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.project_id == project_id,
            BackgroundJob.job_type == "RAG_REINDEX",
        )
        .order_by(BackgroundJob.created_at.desc())
        .limit(1)
    )
    if not job:
        return {"status": "idle", "job": None}
    payload = _reindex_job_payload(job)
    return {"status": payload["status"], "job": payload}


@router.get("/projects/{project_id}/files/original")
async def get_file_original(
    project_id: str,
    path: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get the original (git HEAD) version of a file for diff baseline."""
    project = await _require_project(project_id, current_user, db)
    check_fs_policy(project, "read")
    device_id, workspace = await _resolve_execution_target(project, db)
    tool_res = await ToolGateway.invoke_tool(
        device_id=device_id,
        workspace_id=workspace,
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
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all generated artifacts for a project."""
    from app.repositories.artifact_repo import ArtifactRepository

    repo = ProjectRepository(db)
    if not await repo.belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    artifact_repo = ArtifactRepository(db)
    artifacts = await artifact_repo.list_for_project(project_id)
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


class AgentRunResponse(BaseModel):
    """Schema for a single agent run (persisted pipeline step)."""

    id: str
    instruction_id: str
    agent_name: str
    status: str
    output: str | None = None
    metadata: dict | None = None
    duration_seconds: float = 0.0
    created_at: str | None = None


@router.get("/projects/{project_id}/runs", response_model=List[AgentRunResponse])
async def list_project_runs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=200),
) -> Any:
    """List recent persisted agent runs for a project (via its instructions)."""
    from sqlalchemy import select

    from app.models.agent_run import AgentRun
    from app.models.instruction import Instruction

    repo = ProjectRepository(db)
    if not await repo.belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(AgentRun)
        .join(Instruction, Instruction.id == AgentRun.instruction_id)
        .where(Instruction.project_id == project_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    return [
        AgentRunResponse(
            id=r.id,
            instruction_id=r.instruction_id,
            agent_name=r.agent_name,
            status=r.status,
            output=r.output,
            metadata=r.metadata_json,
            duration_seconds=r.duration_seconds,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in result.scalars().all()
    ]
