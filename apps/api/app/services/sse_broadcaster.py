"""SSE Broadcaster Service using Async Queues for Live Web Updates."""

import asyncio
from typing import Any, Dict, Set, Tuple


class SSEBroadcaster:
    """Manages Server-Sent Event channels for project subscribers.

    This is an in-process fast path: events raised inside the API process are
    delivered to connected SSE clients immediately, while the durable
    ``InstructionEvent`` table remains the source of truth for replay and for
    events produced by the worker process.
    """

    def __init__(self) -> None:
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}

    async def subscribe(self, project_id: str) -> asyncio.Queue:
        """Subscribe a web client queue to the project event channel."""
        queue: asyncio.Queue = asyncio.Queue()
        if project_id not in self.subscribers:
            self.subscribers[project_id] = set()
        self.subscribers[project_id].add(queue)
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        """Remove a client queue from the project event channel."""
        if project_id in self.subscribers:
            self.subscribers[project_id].discard(queue)
            if not self.subscribers[project_id]:
                del self.subscribers[project_id]

    async def notify(
        self,
        project_id: str,
        event_id: int,
        payload: Dict[str, Any],
    ) -> None:
        """Push an in-process event to all active project subscribers.

        Subscribers receive ``(event_id, payload)`` tuples; consumers dedupe
        against the durable replay cursor by ``event_id``.
        """
        if project_id in self.subscribers:
            item: Tuple[int, Dict[str, Any]] = (event_id, payload)
            for queue in self.subscribers[project_id]:
                await queue.put(item)


broadcaster = SSEBroadcaster()
