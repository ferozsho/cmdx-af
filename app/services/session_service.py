from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.session import SessionContext, SessionContextResponse

class SessionService:
    """Service layer for session context tracking."""

    def __init__(self):
        # In-memory storage for demonstration; replace with DB in production
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SessionContextResponse:
        """Create a new session context."""
        if session_id in self._sessions:
            raise ValueError(f"Session {session_id} already exists")
        now = datetime.now(timezone.utc)
        context = SessionContext(session_id=session_id, user_id=user_id, metadata=metadata or {})
        self._sessions[session_id] = {
            "context": context,
            "created_at": now,
            "updated_at": now
        }
        return SessionContextResponse(
            session_id=session_id,
            context=context,
            created_at=now,
            updated_at=now
        )

    def get_session(self, session_id: str) -> Optional[SessionContextResponse]:
        """Retrieve a session context by ID."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return SessionContextResponse(
            session_id=session_id,
            context=session["context"],
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        )

    def update_session_context(self, session_id: str, metadata: Dict[str, Any]) -> Optional[SessionContextResponse]:
        """Update session context metadata."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        # Merge metadata
        session["context"].metadata.update(metadata)
        session["updated_at"] = datetime.now(timezone.utc)
        return SessionContextResponse(
            session_id=session_id,
            context=session["context"],
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        )

    def delete_session(self, session_id: str) -> bool:
        """Delete a session context."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
