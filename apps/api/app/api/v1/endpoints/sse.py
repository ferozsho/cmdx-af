"""Server-Sent Events Endpoint for Live Front-end Updates."""

import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.sse_broadcaster import broadcaster

router = APIRouter()


@router.get("/projects/{project_id}/stream")
async def stream_project_events(project_id: str) -> StreamingResponse:
    """Stream real-time agent execution events to client browser via SSE."""
    queue = await broadcaster.subscribe(project_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            broadcaster.unsubscribe(project_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
