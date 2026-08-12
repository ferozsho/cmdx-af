"""Session Management Endpoints — context window sessions for projects."""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.instruction import Instruction
from app.models.llm_usage import LLMUsage
from app.models.session import Session
from app.models.user import User
from app.repositories.project_repo import ProjectRepository

router = APIRouter()


async def _require_project_owner(
    project_id: str,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Require project ownership without disclosing other users' projects."""
    if not await ProjectRepository(db).belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")


# Model context window limits (tokens)
MODEL_CONTEXT_LIMITS = {
    "deepseek-chat": 65536,         # DeepSeek-V3
    "deepseek-reasoner": 65536,     # DeepSeek-R1
    "deepseek-coder": 131072,       # DeepSeek-Coder (128K)
    "gpt-4o": 131072,               # GPT-4o (128K)
    "gpt-4-turbo": 131072,          # GPT-4 Turbo (128K)
    "gpt-3.5-turbo": 16385,         # GPT-3.5 Turbo (16K)
    "gemini-2.5-pro": 1048576,      # Gemini 2.5 Pro (1M)
    "gemini-2.5-flash": 1048576,    # Gemini 2.5 Flash (1M)
    "gemini-1.5-pro": 2097152,      # Gemini 1.5 Pro (2M)
    "claude-3.5-sonnet": 204800,    # Claude 3.5 Sonnet (200K)
    "claude-3-opus": 204800,        # Claude 3 Opus (200K)
    "claude-3-haiku": 204800,       # Claude 3 Haiku (200K)
}


class SessionCreate(BaseModel):
    name: str = "New Session"
    model_name: str = "deepseek-chat"


class SessionResponse(BaseModel):
    id: str
    project_id: str
    user_id: str | None
    name: str
    model_name: str
    context_limit: int
    total_tokens_used: int
    created_at: str | None
    updated_at: str | None


@router.get(
    "/projects/{project_id}/sessions",
    response_model=List[SessionResponse],
)
async def list_sessions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all sessions for a project."""
    await _require_project_owner(project_id, current_user, db)
    result = await db.execute(
        select(Session)
        .where(Session.project_id == project_id)
        .order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()
    return [
        SessionResponse(
            id=s.id,
            project_id=s.project_id,
            user_id=s.user_id,
            name=s.name,
            model_name=s.model_name,
            context_limit=s.context_limit,
            total_tokens_used=s.total_tokens_used,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
        )
        for s in sessions
    ]


@router.post(
    "/projects/{project_id}/sessions",
    response_model=SessionResponse,
)
async def create_session(
    project_id: str,
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a new context session for a project."""
    await _require_project_owner(project_id, current_user, db)
    context_limit = MODEL_CONTEXT_LIMITS.get(
        data.model_name, 65536
    )
    session = Session(
        project_id=project_id,
        user_id=current_user.id,
        name=data.name,
        model_name=data.model_name,
        context_limit=context_limit,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        project_id=session.project_id,
        user_id=session.user_id,
        name=session.name,
        model_name=session.model_name,
        context_limit=session.context_limit,
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at.isoformat() if session.created_at else None,
        updated_at=session.updated_at.isoformat() if session.updated_at else None,
    )


@router.get(
    "/projects/{project_id}/sessions/{session_id}/context",
)
async def get_session_context(
    project_id: str,
    session_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get accumulated context from previous instructions in a session."""
    await _require_project_owner(project_id, current_user, db)
    session = await db.get(Session, session_id)
    if not session or session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get recent completed instructions with their agent runs
    result = await db.execute(
        select(Instruction)
        .where(
            Instruction.session_id == session_id,
            Instruction.status.in_(["COMPLETED", "FAILED"]),
        )
        .order_by(Instruction.created_at.desc())
        .limit(limit)
    )
    instructions = result.scalars().all()

    # Get aggregated token usage from llm_usage — counts both pipeline calls
    # (linked via instruction) and session-attributed AI calls (e.g. tech-lead
    # queries recorded with session_id directly).
    token_result = await db.execute(
        select(func.coalesce(func.sum(LLMUsage.total_tokens), 0)).where(
            or_(
                LLMUsage.session_id == session_id,
                LLMUsage.instruction_id.in_(
                    select(Instruction.id).where(
                        Instruction.session_id == session_id,
                    )
                ),
            )
        )
    )
    total_tokens = token_result.scalar() or 0

    # Update the session's token count
    session.total_tokens_used = total_tokens
    await db.commit()

    # Build context summary
    context_entries = []
    for ins in reversed(instructions):  # oldest first for context order
        entry = {
            "instruction_id": ins.id,
            "prompt": ins.prompt,
            "status": ins.status,
            "created_at": ins.created_at.isoformat() if ins.created_at else None,
        }
        context_entries.append(entry)

    return {
        "session_id": session_id,
        "model_name": session.model_name,
        "context_limit": session.context_limit,
        "total_tokens_used": total_tokens,
        "context_used_pct": round(
            (total_tokens / session.context_limit * 100) if session.context_limit else 0,
            1,
        ),
        "previous_instructions": context_entries,
    }


class SessionUpdate(BaseModel):
    """Fields allowed when renaming a session."""

    name: Optional[str] = None


@router.patch("/projects/{project_id}/sessions/{session_id}")
async def update_session(
    project_id: str,
    session_id: str,
    data: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Rename a session."""
    await _require_project_owner(project_id, current_user, db)
    session = await db.get(Session, session_id)
    if not session or session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if data.name is not None:
        session.name = data.name
        await db.commit()
    return {"ok": True, "id": session.id, "name": session.name}


@router.delete("/projects/{project_id}/sessions/{session_id}")
async def delete_session(
    project_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete a session and its associated instructions."""
    await _require_project_owner(project_id, current_user, db)
    session = await db.get(Session, session_id)
    if not session or session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Session not found")
    # Cascade delete handles instructions and their dependent rows
    await db.delete(session)
    await db.commit()
    return {"ok": True}
