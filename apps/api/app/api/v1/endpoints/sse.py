"""Authenticated replayable Server-Sent Events endpoint."""

import asyncio
import json
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.models.instruction_event import InstructionEvent
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.services.sse_broadcaster import broadcaster

router = APIRouter()


@router.get("/projects/{project_id}/stream")
async def stream_project_events(
    project_id: str,
    request: Request,
    after: int = Query(0, ge=0),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Replay durable events then follow new events for an owned project.

    Events raised inside this API process are delivered immediately through
    the in-process broadcaster (fast path); everything else — including
    worker-produced events — is picked up by the durable replay poll. Both
    paths are deduplicated by the monotonic ``InstructionEvent.id`` cursor.
    """
    if not await ProjectRepository(db).belongs_to(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        cursor = max(after, int(last_event_id or 0))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Last-Event-ID must be an integer",
        ) from None

    async def event_generator() -> AsyncGenerator[str, None]:
        nonlocal cursor
        last_keepalive = time.monotonic()
        queue = await broadcaster.subscribe(project_id)
        try:
            while not await request.is_disconnected():
                # Fast path: drain in-process broadcaster events first.
                delivered = False
                while True:
                    try:
                        event_id, payload = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    if event_id > cursor:
                        cursor = event_id
                        yield (
                            f"id: {event_id}\n"
                            "event: instruction\n"
                            f"data: {json.dumps(payload)}\n\n"
                        )
                        delivered = True
                if delivered:
                    last_keepalive = time.monotonic()
                    continue
                # Durable path: replay events missed by the fast path (for
                # example events produced by the worker process).
                async with AsyncSessionLocal() as event_db:
                    result = await event_db.execute(
                        select(InstructionEvent)
                        .where(
                            InstructionEvent.project_id == project_id,
                            InstructionEvent.id > cursor,
                        )
                        .order_by(InstructionEvent.id.asc())
                        .limit(100)
                    )
                    events = result.scalars().all()
                if events:
                    for event in events:
                        cursor = event.id
                        yield (
                            f"id: {event.id}\n"
                            "event: instruction\n"
                            f"data: {json.dumps(event.payload)}\n\n"
                        )
                    last_keepalive = time.monotonic()
                    continue
                if time.monotonic() - last_keepalive >= 15:
                    yield ": keepalive\n\n"
                    last_keepalive = time.monotonic()
                await asyncio.sleep(1)
        finally:
            broadcaster.unsubscribe(project_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
