"""Structured Message Schemas for Cloud ↔ Local Agent WSS Communication."""

from enum import Enum
from typing import Any

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

    message_type: MessageType = MessageType.PAIRING_REQUEST
    pairing_code: str = Field(
        ..., description="Temporary pairing code generated in Cloud UI"
    )
    device_name: str = Field(..., description="Developer workstation hostname")
    os_info: str = Field(..., description="OS platform description")
    capabilities: dict[str, Any] = Field(
        default_factory=dict, description="Installed runtimes (python, node, git)"
    )


class PairingResponse(BaseModel):
    """Cloud pairing response containing permanent device token."""

    message_type: MessageType = MessageType.PAIRING_RESPONSE
    success: bool
    device_id: str | None = None
    device_token: str | None = None
    error: str | None = None


class DeviceHeartbeat(BaseModel):
    """Heartbeat message sent periodically by Local Agent."""

    message_type: MessageType = MessageType.HEARTBEAT
    device_id: str
    timestamp: float
    workspaces: list[str] = Field(default_factory=list)


class ToolRequest(BaseModel):
    """Request sent from Cloud Tool Gateway to Local Agent."""

    message_type: MessageType = MessageType.TOOL_REQUEST
    request_id: str
    job_id: str
    workspace_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    authorization_id: str | None = Field(
        default=None,
        description="Policy grant or consumed human-approval identifier",
    )


class ToolResult(BaseModel):
    """Response returned from Local Agent to Cloud Tool Gateway."""

    message_type: MessageType = MessageType.TOOL_RESULT
    request_id: str
    job_id: str
    tool_name: str
    success: bool
    result: Any | None = None
    error: str | None = None
    duration_ms: float = 0.0


class AgentEventMessage(BaseModel):
    """Live execution event broadcasted to SSE frontend."""

    message_type: MessageType = MessageType.AGENT_EVENT
    project_id: str
    instruction_id: str
    event_type: str
    agent_name: str | None = None
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float
