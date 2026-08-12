"""Outbound WSS Client for Local Agent Daemon."""

import asyncio
import contextlib
import json
import logging
import time
from typing import Any, Callable, Coroutine

import websockets
from agentforge_protocol import DeviceHeartbeat, ToolRequest, ToolResult

from agentforge_local.config import local_settings

logger = logging.getLogger("agentforge.local.wss")


class LocalWSSClient:
    """Outbound WebSocket client for connecting Local Agent to Cloud Control Plane."""

    def __init__(
        self,
        cloud_wss_url: str,
        device_id: str,
        device_token: str,
        tool_handler: Callable[[ToolRequest], Coroutine[Any, Any, ToolResult]],
        workspace_ids: Callable[[], list[str]] | None = None,
    ) -> None:
        self.cloud_wss_url = cloud_wss_url
        self.device_id = device_id
        self.device_token = device_token
        self.tool_handler = tool_handler
        self.workspace_ids = workspace_ids or (lambda: [])
        self.running = False

    async def start(self) -> None:
        """Connect to Cloud WSS with auto-reconnect loop."""
        self.running = True
        url = f"{self.cloud_wss_url}/{self.device_id}"
        headers = {"Authorization": f"Bearer {self.device_token}"}

        while self.running:
            try:
                logger.info(f"Connecting to Cloud WSS: {url}")
                async with websockets.connect(
                    url,
                    additional_headers=headers,
                ) as ws:
                    logger.info("✅ Connected to Cloud WSS!")
                    heartbeat_task = asyncio.create_task(
                        self._send_heartbeats(ws)
                    )
                    try:
                        while self.running:
                            message_text = await ws.recv()
                            data = json.loads(message_text)

                            if "tool_name" in data and "request_id" in data:
                                tool_req = ToolRequest.model_validate(data)
                                asyncio.create_task(
                                    self._process_tool_request(ws, tool_req)
                                )
                    finally:
                        heartbeat_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await heartbeat_task

            except websockets.ConnectionClosed:
                logger.warning("Disconnected from Cloud WSS. Reconnecting in 5s...")
            except Exception as e:
                logger.error(f"WSS Connection error: {e}. Retrying in 5s...")

            await asyncio.sleep(5)

    async def _send_heartbeat(self, ws: Any) -> None:
        """Publish one typed heartbeat without exposing local paths."""
        heartbeat = DeviceHeartbeat(
            device_id=self.device_id,
            timestamp=time.time(),
            workspaces=self.workspace_ids(),
        )
        await ws.send(heartbeat.model_dump_json())

    async def _send_heartbeats(self, ws: Any) -> None:
        """Publish liveness for the lifetime of one WSS connection."""
        interval = max(5, int(local_settings.HEARTBEAT_INTERVAL))
        while self.running:
            await self._send_heartbeat(ws)
            await asyncio.sleep(interval)

    async def _process_tool_request(self, ws: Any, tool_req: ToolRequest) -> None:
        """Execute tool handler and transmit ToolResult back to Cloud."""
        try:
            result = await self.tool_handler(tool_req)
        except Exception as e:
            result = ToolResult(
                request_id=tool_req.request_id,
                job_id=tool_req.job_id,
                tool_name=tool_req.tool_name,
                success=False,
                error=str(e),
            )
        try:
            await ws.send(result.model_dump_json())
        except Exception:
            # Connection may have dropped while the tool ran (e.g. keepalive
            # ping timeout or an API container restart). The reconnect loop in
            # start() restores the connection — nothing useful to send here.
            logger.warning(
                "Dropped tool response for %s (connection closed)",
                tool_req.request_id,
            )

    def stop(self) -> None:
        """Stop client daemon."""
        self.running = False
