"""WebSocket Route for Local Agent Device Connections."""

import json

from agentforge_protocol import DeviceHeartbeat, MessageType, ToolResult
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_device_token
from app.repositories.device_repo import DeviceRepository
from app.wss.connection_manager import wss_manager

router = APIRouter()


async def _validate_token(
    db: AsyncSession,
    device_id: str,
    token: str | None,
) -> bool:
    """Validate a required device token against its stored hash."""
    if not token:
        return False
    try:
        repo = DeviceRepository(db)
        device = await repo.get_by_id(device_id)
        if not device:
            return False
        caps = device.capabilities or {}
        return verify_device_token(
            token,
            str(caps.get("device_token_hash") or ""),
        )
    except Exception:
        return False


@router.websocket("/ws/devices/{device_id}")
async def device_websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """WebSocket endpoint for Local Agent device connection."""
    authorization = websocket.headers.get("authorization", "")
    scheme, _, credential = authorization.partition(" ")
    token = credential if scheme.lower() == "bearer" else None
    if not await _validate_token(db, device_id, token):
        await websocket.close(code=4401, reason="Invalid device token")
        return

    await wss_manager.connect(device_id, websocket, db)
    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            msg_type = data.get("type") or data.get("message_type")

            if msg_type == MessageType.HEARTBEAT:
                heartbeat = DeviceHeartbeat.model_validate(data)
                if heartbeat.device_id != device_id:
                    await websocket.close(
                        code=4403,
                        reason="Heartbeat device ID mismatch",
                    )
                    return
                await DeviceRepository(db).record_heartbeat(
                    device_id,
                    heartbeat.workspaces,
                )
                await db.commit()
            elif msg_type == MessageType.TOOL_RESULT or "request_id" in data:
                tool_res = ToolResult.model_validate(data)
                wss_manager.handle_tool_result(tool_res)

    except WebSocketDisconnect:
        await wss_manager.disconnect(device_id, db)
    except Exception:
        await wss_manager.disconnect(device_id, db)
