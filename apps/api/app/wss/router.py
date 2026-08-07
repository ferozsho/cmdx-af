"""WebSocket Route for Local Agent Device Connections."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agentforge_protocol import MessageType, ToolResult
from app.core.database import get_db
from app.wss.connection_manager import wss_manager

router = APIRouter()


@router.websocket("/ws/devices/{device_id}")
async def device_websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """WebSocket endpoint for Local Agent device connection."""
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
