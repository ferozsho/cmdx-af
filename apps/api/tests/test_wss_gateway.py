"""Typed cloud WebSocket gateway request/response tests."""

import asyncio
import json
from typing import Any

import httpx
import pytest
from agentforge_protocol import ToolRequest, ToolResult
from fastapi import HTTPException

from app.api.v1.endpoints import internal as internal_endpoint
from app.api.v1.endpoints.internal import ToolInvokePayload, internal_invoke_tool
from app.core.config import settings
from app.tools.gateway import tool_gateway as tool_gateway_module
from app.tools.gateway.tool_gateway import ToolGateway
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


@pytest.mark.asyncio
async def test_worker_gateway_relays_request_to_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker relay preserves correlation and service credentials."""
    captured: dict[str, Any] = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, str],
        ) -> httpx.Response:
            captured.update(url=url, json=json, headers=headers)
            return httpx.Response(
                200,
                json={
                    "request_id": json["request_id"],
                    "job_id": json["job_id"],
                    "tool_name": json["tool_name"],
                    "success": True,
                    "result": {"written": True},
                    "error": None,
                    "duration_ms": 12.5,
                },
            )

    monkeypatch.setattr(settings, "TOOL_GATEWAY_URL", "http://api:8000/")
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "relay-test-token")
    monkeypatch.setattr(tool_gateway_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await ToolGateway.invoke_tool(
        device_id="device-test",
        workspace_id="workspace-test",
        job_id="job-test",
        tool_name="write_file",
        arguments={"path": "result.txt", "content": "done"},
        authorization_id="approval-test",
    )

    assert result.success is True
    assert result.result == {"written": True}
    assert captured["url"] == "http://api:8000/api/v1/internal/tools/invoke"
    assert captured["headers"] == {"X-Internal-Token": "relay-test-token"}
    assert captured["json"]["request_id"] == result.request_id
    assert captured["json"]["authorization_id"] == "approval-test"


@pytest.mark.asyncio
async def test_worker_gateway_fails_closed_without_internal_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A relay never sends an unauthenticated internal request."""
    monkeypatch.setattr(settings, "TOOL_GATEWAY_URL", "http://api:8000")
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "")

    result = await ToolGateway.invoke_tool(
        device_id="device-test",
        workspace_id="workspace-test",
        job_id="job-test",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )

    assert result.success is False
    assert result.error == "Tool gateway relay is missing INTERNAL_API_TOKEN."


@pytest.mark.asyncio
async def test_internal_relay_authenticates_and_preserves_request_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The API boundary authenticates the worker and forwards its request."""
    captured: dict[str, Any] = {}

    async def fake_send_tool_request(
        device_id: str,
        request: ToolRequest,
    ) -> ToolResult:
        captured.update(device_id=device_id, request=request)
        return ToolResult(
            request_id=request.request_id,
            job_id=request.job_id,
            tool_name=request.tool_name,
            success=True,
            result={"echo": request.arguments},
        )

    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "relay-test-token")
    monkeypatch.setattr(
        internal_endpoint.wss_manager,
        "send_tool_request",
        fake_send_tool_request,
    )
    payload = ToolInvokePayload(
        request_id="request-relay",
        device_id="device-test",
        workspace_id="workspace-test",
        job_id="job-test",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )

    response = await internal_invoke_tool(
        payload,
        x_internal_token="relay-test-token",
    )

    assert response["request_id"] == "request-relay"
    assert captured["device_id"] == "device-test"
    assert captured["request"].workspace_id == "workspace-test"

    with pytest.raises(HTTPException) as exc_info:
        await internal_invoke_tool(payload, x_internal_token="wrong-token")
    assert exc_info.value.status_code == 401
