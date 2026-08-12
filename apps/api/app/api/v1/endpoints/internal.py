"""Internal service-to-service endpoints (worker → API tool relay)."""

import secrets
from typing import Any

from agentforge_protocol import ToolRequest
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.wss.connection_manager import wss_manager

router = APIRouter()


class ToolInvokePayload(BaseModel):
    """Tool dispatch payload from the worker's tool gateway."""

    request_id: str
    device_id: str
    workspace_id: str
    job_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    authorization_id: str | None = None


@router.post("/internal/tools/invoke")
async def internal_invoke_tool(
    payload: ToolInvokePayload,
    x_internal_token: str = Header(default=""),
) -> dict[str, Any]:
    """Relay a tool call to a live device over WSS.

    The instruction worker runs in a separate process from the API and holds
    no WebSocket connections, so it dispatches tool calls here; the API
    relays them over its live device sockets and returns the result.
    """
    if (
        not settings.INTERNAL_API_TOKEN
        or not secrets.compare_digest(
            x_internal_token,
            settings.INTERNAL_API_TOKEN,
        )
    ):
        raise HTTPException(status_code=401, detail="Invalid internal token")

    req = ToolRequest(
        request_id=payload.request_id,
        job_id=payload.job_id,
        workspace_id=payload.workspace_id,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
        authorization_id=payload.authorization_id,
    )
    result = await wss_manager.send_tool_request(payload.device_id, req)
    return {
        "request_id": result.request_id,
        "job_id": result.job_id,
        "tool_name": result.tool_name,
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }
