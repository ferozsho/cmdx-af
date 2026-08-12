"""Typed cloud WebSocket gateway request/response tests."""

import asyncio
import json

import pytest
from agentforge_protocol import ToolRequest, ToolResult

from app.wss.connection_manager import WSSConnectionManager


class LoopbackWebSocket:
    """Return a successful typed result for each outbound tool request."""

    def __init__(self, manager: WSSConnectionManager) -> None:
        self.manager = manager
        self.messages: list[dict] = []

    async def send_text(self, message: str) -> None:
        payload = json.loads(message)
        self.messages.append(payload)
        result = ToolResult(
            request_id=payload["request_id"],
            job_id=payload["job_id"],
            tool_name=payload["tool_name"],
            success=True,
            result={"echo": payload["arguments"]},
        )
        asyncio.get_running_loop().call_soon(
            self.manager.handle_tool_result,
            result,
        )


@pytest.mark.asyncio
async def test_gateway_round_trip_uses_typed_protocol() -> None:
    """A tool result resolves exactly the matching pending cloud request."""
    manager = WSSConnectionManager()
    websocket = LoopbackWebSocket(manager)
    manager.active_connections["device-test"] = websocket  # type: ignore[assignment]
    request = ToolRequest(
        request_id="request-test",
        job_id="job-test",
        workspace_id="workspace-test",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )

    result = await manager.send_tool_request("device-test", request)

    assert result.success is True
    assert result.result == {"echo": {"path": "README.md"}}
    assert websocket.messages[0]["message_type"] == "tool_request"
    assert manager.pending_requests == {}


@pytest.mark.asyncio
async def test_gateway_fails_closed_for_offline_device() -> None:
    """Requests cannot appear successful when no authenticated socket exists."""
    manager = WSSConnectionManager()
    request = ToolRequest(
        request_id="request-offline",
        job_id="job-test",
        workspace_id="workspace-test",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )

    result = await manager.send_tool_request("missing-device", request)

    assert result.success is False
    assert "offline" in (result.error or "")
