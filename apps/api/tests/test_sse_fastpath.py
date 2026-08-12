"""Tests for the SSE in-process fast path (G2).

The SSE endpoint cannot be exercised over ``httpx.ASGITransport`` (streaming
responses never surface their headers through that transport in this stack),
so these tests drive the endpoint's async generator directly via
``StreamingResponse.body_iterator`` and verify the broadcaster wiring at the
service level.
"""

import asyncio
import uuid
from typing import Any, AsyncIterator

import httpx
import pytest
import pytest_asyncio
from starlette.requests import Request

from app.api.v1.endpoints.sse import stream_project_events
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.instruction import Instruction
from app.models.instruction_event import InstructionEvent
from app.models.user import User
from app.services.instruction_events import append_instruction_event
from app.services.sse_broadcaster import broadcaster

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def _register_project(
    api_client: httpx.AsyncClient,
) -> tuple[dict[str, str], str, str]:
    """Register a unique user and create an owned project."""
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"sse-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "SSE Fast Path",
        },
    )
    assert registered.status_code == 201, registered.text
    auth = registered.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    created = await api_client.post(
        "/api/v1/projects", headers=headers, json={"name": f"SSE {suffix}"}
    )
    assert created.status_code == 200, created.text
    return headers, created.json()["id"], auth["user"]["id"]


async def _delete_project(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> None:
    """Delete the project so its events/instructions cascade away."""
    response = await api_client.delete(
        f"/api/v1/projects/{project_id}", headers=headers
    )
    assert response.status_code == 200, response.text


async def _insert_instruction(
    project_id: str, user_id: str, instruction_id: str
) -> None:
    """Insert the instruction row the event FK requires."""
    async with AsyncSessionLocal() as session:
        session.add(
            Instruction(
                id=instruction_id,
                project_id=project_id,
                user_id=user_id,
                prompt="SSE fast-path test",
                status="PENDING",
            )
        )
        await session.commit()


async def _fake_receive():
    """A non-disconnect receive channel for the constructed Request."""
    return {"type": "http.request", "body": b""}


def _make_request(project_id: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/api/v1/projects/{project_id}/stream",
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
        },
        receive=_fake_receive,
    )


async def _start_generator(project_id: str, user_id: str) -> Any:
    """Return the SSE endpoint's body iterator wired to a real user."""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        response = await stream_project_events(
            project_id=project_id,
            request=_make_request(project_id),
            after=0,
            last_event_id=None,
            db=session,
            current_user=user,
        )
        return response.body_iterator


async def _collect_until(
    body_iterator: AsyncIterator[bytes],
    marker: str,
    timeout: float = 8.0,
) -> str:
    """Collect SSE chunks until the marker appears or the timeout elapses."""
    buffer = ""
    try:
        async with asyncio.timeout(timeout):
            async for chunk in body_iterator:
                buffer += chunk.decode() if isinstance(chunk, bytes) else chunk
                if marker in buffer:
                    return buffer
    except TimeoutError:
        pass
    return buffer


async def _count_in_stream(
    body_iterator: AsyncIterator[bytes],
    marker: str,
    duration: float = 3.0,
) -> int:
    """Count occurrences of a marker while reading the stream for a while."""
    buffer = ""
    try:
        async with asyncio.timeout(duration):
            async for chunk in body_iterator:
                buffer += chunk.decode() if isinstance(chunk, bytes) else chunk
    except TimeoutError:
        pass
    return buffer.count(marker)


async def test_broadcaster_delivers_immediately() -> None:
    """The in-process broadcaster hands events to subscribers with no poll."""
    queue = await broadcaster.subscribe("proj-bcast")
    try:
        await broadcaster.notify("proj-bcast", 42, {"message": "hi"})
        event_id, payload = queue.get_nowait()
        assert event_id == 42
        assert payload == {"message": "hi"}
    finally:
        broadcaster.unsubscribe("proj-bcast", queue)


async def test_append_event_notifies_subscribers(api_client) -> None:
    """Persisting an event also pushes it to in-process subscribers (G2)."""
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    await _insert_instruction(project_id, user_id, instruction_id)
    try:
        queue = await broadcaster.subscribe(project_id)
        try:
            payload = {
                "agent_name": "System",
                "status": "PENDING",
                "message": "notify-me",
            }
            event = await append_instruction_event(
                project_id, instruction_id, payload
            )
            event_id, delivered = queue.get_nowait()
            assert event_id == event.id
            assert delivered["message"] == "notify-me"
        finally:
            broadcaster.unsubscribe(project_id, queue)
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_generator_fastpath_delivers_in_process_event(api_client) -> None:
    """An in-process event reaches the SSE generator without DB-poll delay."""
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    await _insert_instruction(project_id, user_id, instruction_id)
    try:
        body_iterator = await _start_generator(project_id, user_id)
        marker = "fast-path-marker"
        collect_task = asyncio.create_task(
            _collect_until(body_iterator, marker)
        )
        await asyncio.sleep(0.2)  # let the generator subscribe and start
        await append_instruction_event(
            project_id,
            instruction_id,
            {"agent_name": "System", "status": "PENDING", "message": marker},
        )
        out = await asyncio.wait_for(collect_task, timeout=10)
        assert marker in out
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_generator_deduplicates_both_paths(api_client) -> None:
    """Fast-path delivery plus durable replay yields the event exactly once."""
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    await _insert_instruction(project_id, user_id, instruction_id)
    try:
        body_iterator = await _start_generator(project_id, user_id)
        marker = "no-dup-marker"
        count_task = asyncio.create_task(_count_in_stream(body_iterator, marker))
        await asyncio.sleep(0.2)
        await append_instruction_event(
            project_id,
            instruction_id,
            {"agent_name": "System", "status": "PENDING", "message": marker},
        )
        count = await asyncio.wait_for(count_task, timeout=10)
        assert count == 1
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_generator_replays_durable_events(api_client) -> None:
    """Worker-process events (DB only, no broadcaster) arrive via replay."""
    headers, project_id, user_id = await _register_project(api_client)
    instruction_id = f"ins_{uuid.uuid4().hex[:8]}"
    await _insert_instruction(project_id, user_id, instruction_id)
    try:
        # Simulate an event written by the worker process: insert directly
        # into the DB, bypassing the in-process broadcaster entirely.
        async with AsyncSessionLocal() as session:
            session.add(
                InstructionEvent(
                    project_id=project_id,
                    instruction_id=instruction_id,
                    payload={
                        "agent_name": "System",
                        "status": "RUNNING",
                        "message": "worker-event-marker",
                    },
                )
            )
            await session.commit()

        body_iterator = await _start_generator(project_id, user_id)
        out = await asyncio.wait_for(
            _collect_until(body_iterator, "worker-event-marker"), timeout=10
        )
        assert "worker-event-marker" in out
    finally:
        await _delete_project(api_client, headers, project_id)
