from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class SessionContext(BaseModel):
    """Schema for session context data."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier if authenticated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")

class SessionContextResponse(BaseModel):
    """Response schema for session context."""
    session_id: str
    context: SessionContext
    created_at: datetime
    updated_at: datetime
