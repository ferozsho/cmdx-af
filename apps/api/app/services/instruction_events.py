"""Persistence helpers for replayable instruction events."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.instruction_event import InstructionEvent
from app.services.sse_broadcaster import broadcaster


async def append_instruction_event(
    project_id: str,
    instruction_id: str,
    payload: dict,
    db: AsyncSession | None = None,
) -> InstructionEvent:
    """Persist an event, using the caller transaction when supplied.

    After the event id is assigned, subscribers are notified over the
    in-process broadcaster (fast path); the durable row remains the source
    of truth for replay and worker-produced events.
    """
    event = InstructionEvent(
        project_id=project_id,
        instruction_id=instruction_id,
        payload=payload,
    )
    if db is not None:
        db.add(event)
        await db.flush()
        await broadcaster.notify(project_id, event.id, payload)
        return event

    async with AsyncSessionLocal() as session:
        session.add(event)
        await session.commit()
        await session.refresh(event)
        await broadcaster.notify(project_id, event.id, payload)
        return event
