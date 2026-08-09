from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.session import SessionContext, SessionContextResponse, SessionContextUpdate

class SessionService:
    """Service layer for session context tracking."""

    def __init__(self):
        # In-memory storage for demonstration; replace with DB in production.
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, context: SessionContext) -> SessionContextResponse:
        """Create a new session context."""
        now = datetime.now(timezone.utc)
        session_data = {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "context": context.metadata,
            "created_at": now,
            "updated_at": now,
        }
        self._sessions[context.session_id] = session_data
        return SessionContextResponse(**session_data)

    def get_session(self, session_id: str) -> Optional[SessionContextResponse]:
        """Retrieve session context by session ID."""
        session = self._sessions.get(session_id)
        if session:
            return SessionContextResponse(**session)
        return None

    def update_session(self, session_id: str, update: SessionContextUpdate) -> Optional[SessionContextResponse]:
        """Update session context metadata."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        session["context"].update(update.metadata)
        session["updated_at"] = datetime.now(timezone.utc)
        return SessionContextResponse(**session)

    def delete_session(self, session_id: str) -> bool:
        """Delete session context."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
