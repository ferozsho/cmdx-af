"""Tests for the SSE in-process fast path (G2).

The SSE endpoint combines an in-process broadcaster fast path (for events
raised inside the API process) with the durable ``InstructionEvent`` replay
poll (source of truth + worker-process events). These tests assert immediate
delivery and that the two paths never double-deliver.
"""

import asyncio
import json
import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app
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
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"sse-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "SSE Test",
        },
    )
    assert registered.status_code == 201, registered.text
    body = registered.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    created = await api_client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": f"SSE Project {suffix}"},
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]
    queued = await api_client.post(
        f"/api/v1/projects/{project_id}/instructions",
        headers=headers,
        json={"prompt": "SSE fast-path test"},
    )
    assert queued.status_code == 202, queued.text
    instruction_id = queued.json()["id"]
    return headers, project_id, instruction_id


async def test_broadcaster_delivers_immediately() -> None:
    """The in-process broadcaster pushes (event_id, payload) tuples."""
    project_id = f"proj-{uuid.uuid4().hex}"
    queue = await broadcaster.subscribe(project_id)
    try:
        await broadcaster.notify(project_id, 42, {"message": "hi"})
        event_id, payload = queue.get_nowait()
        assert event_id == 42
        assert payload == {"message": "hi"}
    finally:
        broadcaster.unsubscribe(project_id, queue)


async def _collect_until_marker(
    api_client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    marker: str,
    settle_seconds: float = 0.0,
) -> list[dict]:
    """Read SSE data blocks.

    Collect until the marker message appears (returning immediately unless
    ``settle_seconds`` is set, in which case collection continues for that
    window so duplicate deliveries can be detected).
    """
    payloads: list[dict] = []
    async with api_client.stream("GET", url, headers=headers) as response:
        deadline = None
        try:
            async with asyncio.timeout(10 + settle_seconds):
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        payload = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    payloads.append(payload)
                    if payload.get("message") == marker:
                        if settle_seconds <= 0:
                            return payloads
                        deadline = (
                            asyncio.get_running_loop().time() + settle_seconds
                        )
                        continue
                    if (
                        deadline is not None
                        and asyncio.get_running_loop().time() > deadline
                    ):
                        return payloads
        except TimeoutError:
            pass
    return payloads


async def test_sse_fast_path_delivers_in_process_event(api_client) -> None:
    """An event raised in this process reaches the stream immediately."""
    headers, project_id, instruction_id = await _register_project(api_client)
    marker = f"fast-path-{uuid.uuid4().hex}"
    url = f"/api/v1/projects/{project_id}/stream"
    reader = asyncio.create_task(
        _collect_until_marker(api_client, url, headers, marker)
    )
    # Give the generator time to subscribe to the broadcaster.
    await asyncio.sleep(0.4)
    await append_instruction_event(
        project_id,
        instruction_id,
        {"agent_name": "System", "status": "PENDING", "message": marker},
    )
    payloads = await asyncio.wait_for(reader, timeout=12)
    assert any(p.get("message") == marker for p in payloads), (
        "in-process event should arrive over the SSE stream"
    )


async def test_sse_no_duplicate_across_both_paths(api_client) -> None:
    """Fast-path delivery plus durable replay never double-deliver."""
    headers, project_id, instruction_id = await _register_project(api_client)
    marker = f"no-dup-{uuid.uuid4().hex}"
    url = f"/api/v1/projects/{project_id}/stream"
    reader = asyncio.create_task(
        _collect_until_marker(
            api_client, url, headers, marker, settle_seconds=2.0
        )
    )
    await asyncio.sleep(0.4)
    await append_instruction_event(
        project_id,
        instruction_id,
        {"agent_name": "System", "status": "PENDING", "message": marker},
    )
    payloads = await asyncio.wait_for(reader, timeout=15)
    matches = [p for p in payloads if p.get("message") == marker]
    assert len(matches) == 1, (
        f"expected exactly 1 delivery, got {len(matches)}"
    )
