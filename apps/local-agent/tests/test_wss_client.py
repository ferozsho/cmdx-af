"""Typed local-agent WebSocket protocol tests."""

import json
from typing import Any

import pytest

from agentforge_local.connection.wss_client import LocalWSSClient


class RecordingWebSocket:
    """Minimal websocket test double that records outbound messages."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


async def unused_handler(request: Any) -> Any:
    raise AssertionError(f"Unexpected tool request: {request}")


@pytest.mark.asyncio
async def test_heartbeat_is_typed_and_contains_workspace_ids() -> None:
    websocket = RecordingWebSocket()
    client = LocalWSSClient(
        "ws://cloud.test/ws",
        "device-1",
        "test-token",
        unused_handler,
        workspace_ids=lambda: ["workspace-b", "workspace-a"],
    )

    await client._send_heartbeat(websocket)

    payload = json.loads(websocket.messages[0])
    assert payload["message_type"] == "heartbeat"
    assert payload["device_id"] == "device-1"
    assert payload["workspaces"] == ["workspace-b", "workspace-a"]
    assert payload["timestamp"] > 0
