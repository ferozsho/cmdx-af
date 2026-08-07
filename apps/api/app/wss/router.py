"""WebSocket Route for Local Agent Device Connections."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agentforge_protocol import MessageType, ToolResult
from app.wss.connection_manager import wss_manager

router = APIRouter()


@router.websocket("/ws/devices/{device_id}")
async def device_websocket_endpoint(websocket: WebSocket, device_id: str) -> None:
    """WebSocket endpoint for Local Agent device connection."""
    await wss_manager.connect(device_id, websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            msg_type = data.get("type") or data.get("message_type")

            if msg_type == MessageType.TOOL_RESULT or "request_id" in data:
                tool_res = ToolResult.model_validate(data)
                wss_manager.handle_tool_result(tool_res)

    except WebSocketDisconnect:
        wss_manager.disconnect(device_id)
    except Exception:
        wss_manager.disconnect(device_id)
