"""WSS Connection Manager for Local Agent Device Communication."""

import asyncio
from typing import Dict

from agentforge_protocol import ToolRequest, ToolResult
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.device_repo import DeviceRepository


class WSSConnectionManager:
    """Manages active WebSocket connections to registered Local Agent devices."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_requests: Dict[str, asyncio.Future[ToolResult]] = {}

    async def connect(
        self,
        device_id: str,
        websocket: WebSocket,
        db: AsyncSession | None = None,
    ) -> None:
        """Accept connection, register device in DB, and track as active."""
        await websocket.accept()
        self.active_connections[device_id] = websocket

        if db:
            try:
                repo = DeviceRepository(db)
                device = await repo.get_by_id(device_id)
                if device:
                    await repo.update_status(device_id, "online")
                else:
                    await repo.create(
                        name=device_id,
                        hostname="auto-registered",
                        platform="unknown",
                    )
                    await repo.update_status(device_id, "online")
                await db.commit()
            except Exception:
                pass

    async def disconnect(
        self,
        device_id: str,
        db: AsyncSession | None = None,
    ) -> None:
        """Unregister device socket and mark offline in DB."""
        if device_id in self.active_connections:
            del self.active_connections[device_id]

        if db:
            try:
                repo = DeviceRepository(db)
                await repo.update_status(device_id, "offline")
                await db.commit()
            except Exception:
                pass

    def is_device_online(self, device_id: str) -> bool:
        """Check if device is currently connected."""
        return device_id in self.active_connections

    async def send_tool_request(self, device_id: str, request: ToolRequest) -> ToolResult:
        """Send tool request to device socket and await result asynchronously."""
        if device_id not in self.active_connections:
            return ToolResult(
                request_id=request.request_id,
                job_id=request.job_id,
                tool_name=request.tool_name,
                success=False,
                error=f"Device '{device_id}' is offline.",
            )

        websocket = self.active_connections[device_id]
        future: asyncio.Future[ToolResult] = asyncio.get_running_loop().create_future()
        self.pending_requests[request.request_id] = future

        await websocket.send_text(request.model_dump_json())

        try:
            result = await asyncio.wait_for(future, timeout=120.0)
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                request_id=request.request_id,
                job_id=request.job_id,
                tool_name=request.tool_name,
                success=False,
                error=f"Tool request '{request.tool_name}' timed out after 120s.",
            )
        finally:
            self.pending_requests.pop(request.request_id, None)

    def handle_tool_result(self, result: ToolResult) -> None:
        """Receive tool result and resolve waiting future."""
        future = self.pending_requests.get(result.request_id)
        if future and not future.done():
            future.set_result(result)


wss_manager = WSSConnectionManager()
