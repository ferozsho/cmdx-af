from fastapi import APIRouter, HTTPException, status
from app.schemas.session import SessionContext, SessionContextResponse, SessionContextUpdate
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Initialize service (in real app, use dependency injection)
service = SessionService()

@router.post("/", response_model=SessionContextResponse, status_code=status.HTTP_201_CREATED)
async def create_session(context: SessionContext):
    """Create a new session context."""
    return service.create_session(context)

@router.get("/{session_id}", response_model=SessionContextResponse)
async def get_session(session_id: str):
    """Retrieve session context by ID."""
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.put("/{session_id}", response_model=SessionContextResponse)
async def update_session(session_id: str, update: SessionContextUpdate):
    """Update session context metadata."""
    session = service.update_session(session_id, update)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    """Delete session context."""
    deleted = service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return None
