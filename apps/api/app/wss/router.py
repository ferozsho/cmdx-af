"""WebSocket Route for Local Agent Device Connections."""

import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agentforge_protocol import MessageType, ToolResult
from app.core.database import get_db
from app.repositories.device_repo import DeviceRepository
from app.wss.connection_manager import wss_manager

router = APIRouter()


async def _validate_token(
    db: AsyncSession,
    device_id: str,
    token: Optional[str],
) -> bool:
    """Validate a device token when one is configured for the device.

    Devices with no stored token are allowed to connect (legacy mode);
    devices with a stored token must present a matching token.
    """
    if not token:
        return True
    try:
        repo = DeviceRepository(db)
        device = await repo.get_by_id(device_id)
        if not device:
            return False
        caps = device.capabilities or {}
        stored = caps.get("device_token")
        if not stored:
            return True
        return stored == token
    except Exception:
        return False


@router.websocket("/ws/devices/{device_id}")
async def device_websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """WebSocket endpoint for Local Agent device connection."""
    if not await _validate_token(db, device_id, token):
        await websocket.close(code=4401, reason="Invalid device token")
        return

    await wss_manager.connect(device_id, websocket, db)
    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            msg_type = data.get("type") or data.get("message_type")

            if msg_type == MessageType.TOOL_RESULT or "request_id" in data:
                tool_res = ToolResult.model_validate(data)
                wss_manager.handle_tool_result(tool_res)

    except WebSocketDisconnect:
        await wss_manager.disconnect(device_id, db)
    except Exception:
        await wss_manager.disconnect(device_id, db)
