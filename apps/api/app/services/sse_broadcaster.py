"""SSE Broadcaster Service using Async Queues for Live Web Updates."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Set


class SSEBroadcaster:
    """Manages Server-Sent Event channels for project subscribers."""

    def __init__(self) -> None:
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}

    async def subscribe(self, project_id: str) -> asyncio.Queue:
        """Subscribe web client queue to project event channel."""
        queue: asyncio.Queue = asyncio.Queue()
        if project_id not in self.subscribers:
            self.subscribers[project_id] = set()
        self.subscribers[project_id].add(queue)
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe web client queue from project event channel."""
        if project_id in self.subscribers:
            self.subscribers[project_id].discard(queue)
            if not self.subscribers[project_id]:
                del self.subscribers[project_id]

    async def broadcast(self, project_id: str, event_data: dict) -> None:
        """Broadcast event dictionary to all active project subscribers."""
        if project_id in self.subscribers:
            for queue in self.subscribers[project_id]:
                await queue.put(event_data)


broadcaster = SSEBroadcaster()
