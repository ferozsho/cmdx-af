from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class SessionContext(BaseModel):
    """Schema for session context data."""
    user_id: str = Field(..., description="Unique identifier for the user")
    session_id: str = Field(..., description="Unique identifier for the session")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context metadata")

class SessionContextResponse(BaseModel):
    """Response schema for session context."""
    session_id: str
    user_id: str
    context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class SessionContextUpdate(BaseModel):
    """Schema for updating session context."""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Updated metadata")
