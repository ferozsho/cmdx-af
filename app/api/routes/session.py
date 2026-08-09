from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
from app.schemas.session import SessionContext, SessionContextResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Dependency to get service instance
def get_session_service() -> SessionService:
    return SessionService()

@router.post("/", response_model=SessionContextResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session: SessionContext,
    service: SessionService = Depends(get_session_service)
):
    """Create a new session context."""
    try:
        return service.create_session(
            session_id=session.session_id,
            user_id=session.user_id,
            metadata=session.metadata
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/{session_id}", response_model=SessionContextResponse)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Get session context by ID."""
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

@router.put("/{session_id}", response_model=SessionContextResponse)
def update_session(
    session_id: str,
    metadata: Dict[str, Any],
    service: SessionService = Depends(get_session_service)
):
    """Update session context metadata."""
    session = service.update_session_context(session_id, metadata)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Delete session context."""
    deleted = service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return None
