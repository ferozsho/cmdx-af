"""Structured Message Schemas for Cloud ↔ Local Agent WSS Communication."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Supported WSS Protocol Message Types."""

    PAIRING_REQUEST = "pairing_request"
    PAIRING_RESPONSE = "pairing_response"
    HEARTBEAT = "heartbeat"
    TOOL_REQUEST = "tool_request"
    TOOL_RESULT = "tool_result"
    AGENT_EVENT = "agent_event"


class PairingRequest(BaseModel):
    """Device pairing request sent from Local Agent to Cloud."""

    pairing_code: str = Field(
        ..., description="8-character pairing code generated in Cloud UI"
    )
    device_name: str = Field(..., description="Developer workstation hostname")
    os_info: str = Field(..., description="OS platform description")
    capabilities: Dict[str, Any] = Field(
        default_factory=dict, description="Installed runtimes (python, node, git)"
    )


class PairingResponse(BaseModel):
    """Cloud pairing response containing permanent device token."""

    success: bool
    device_id: Optional[str] = None
    device_token: Optional[str] = None
    error: Optional[str] = None


class DeviceHeartbeat(BaseModel):
    """Heartbeat message sent periodically by Local Agent."""

    device_id: str
    timestamp: float
    workspaces: list[str] = Field(default_factory=list)


class ToolRequest(BaseModel):
    """Request sent from Cloud Tool Gateway to Local Agent."""

    request_id: str
    job_id: str
    workspace_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Response returned from Local Agent to Cloud Tool Gateway."""

    request_id: str
    job_id: str
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class AgentEventMessage(BaseModel):
    """Live execution event broadcasted to SSE frontend."""

    project_id: str
    instruction_id: str
    event_type: str
    agent_name: Optional[str] = None
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float
