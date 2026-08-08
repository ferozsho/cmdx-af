"""Outbound WSS Client for Local Agent Daemon."""

import asyncio
import json
import logging
from typing import Callable, Coroutine, Dict, Any
import websockets
from agentforge_protocol import ToolRequest, ToolResult
from agentforge_local.connection.device_auth import load_device_credentials

logger = logging.getLogger("agentforge.local.wss")


class LocalWSSClient:
    """Outbound WebSocket client for connecting Local Agent to Cloud Control Plane."""

    def __init__(
        self,
        cloud_wss_url: str,
        device_id: str,
        tool_handler: Callable[[ToolRequest], Coroutine[Any, Any, ToolResult]],
    ) -> None:
        self.cloud_wss_url = cloud_wss_url
        self.device_id = device_id
        self.tool_handler = tool_handler
        self.running = False

    async def start(self) -> None:
        """Connect to Cloud WSS with auto-reconnect loop."""
        self.running = True
        url = f"{self.cloud_wss_url}/{self.device_id}"
        token = load_device_credentials().get("device_token")
        if token:
            url = f"{url}?token={token}"

        while self.running:
            try:
                logger.info(f"Connecting to Cloud WSS: {url}")
                async with websockets.connect(url) as ws:
                    logger.info("✅ Connected to Cloud WSS!")
                    while self.running:
                        message_text = await ws.recv()
                        data = json.loads(message_text)

                        if "tool_name" in data and "request_id" in data:
                            tool_req = ToolRequest.model_validate(data)
                            asyncio.create_task(self._process_tool_request(ws, tool_req))

            except websockets.ConnectionClosed:
                logger.warning("Disconnected from Cloud WSS. Reconnecting in 5s...")
            except Exception as e:
                logger.error(f"WSS Connection error: {e}. Retrying in 5s...")

            await asyncio.sleep(5)

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
