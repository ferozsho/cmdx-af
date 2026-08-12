"""Tests for the RAG readiness gate (auto re-index + project access gating)."""

import uuid
from typing import Any

import httpx
import pytest
import pytest_asyncio

from app.core.database import AsyncSessionLocal
from app.core.time import naive_utcnow
from app.main import app
from app.models.project import Project
from app.services.rag_gate import (
    GATE_STATE_COMPLETE,
    GATE_STATE_INDEXING,
    GATE_STATE_OFFLINE,
    active_reindex_job,
    compute_readiness,
    ensure_reindex_job,
    persisted_gate,
)
from tests.helpers import seed_rag_indexed

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api_client():
    """ASGI-native client against the FastAPI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def _create_user_project(
    api_client: httpx.AsyncClient,
) -> tuple[dict[str, str], str, str]:
    """Register a unique user and create an owned (gated) project."""
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"gate-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "Gate Test",
        },
    )
    assert registered.status_code == 201, registered.text
    auth = registered.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    created = await api_client.post(
        "/api/v1/projects", headers=headers, json={"name": f"Gate {suffix}"}
    )
    assert created.status_code == 200, created.text
    return headers, created.json()["id"], auth["user"]["id"]


async def _load_project(project_id: str) -> Project:
    async with AsyncSessionLocal() as db:
        project = await db.get(Project, project_id)
        assert project is not None
        return project


async def _delete_project(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> None:
    response = await api_client.delete(
        f"/api/v1/projects/{project_id}", headers=headers
    )
    assert response.status_code == 200, response.text


async def test_new_project_reports_locked_gate_but_content_is_not_blocked(
    api_client,
) -> None:
    """A fresh project reports rag_gate.locked for cards, but content works.

    The RAG gate is enforced at the entry points (dashboard + Live Workspace
    cards), NOT on project content endpoints — opening a project never shows
    a gate screen.
    """
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        detail = await api_client.get(
            f"/api/v1/projects/{project_id}", headers=headers
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["rag_gate"]["locked"] is True
        assert detail.json()["rag_gate"]["state"] != "complete"

        # Content endpoints are NOT gated: instruction submit and tree work
        # regardless of RAG index state.
        res = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions",
            headers=headers,
            json={"prompt": "run the pipeline"},
        )
        assert res.status_code == 202, res.text
        assert res.json()["status"] == "PENDING"

        tree = await api_client.get(
            f"/api/v1/projects/{project_id}/tree", headers=headers
        )
        assert tree.status_code != 423, tree.text
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_project_unlocks_after_index_seeded(api_client) -> None:
    """Once rag_indexed_at is set the gate is open and content works."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        await seed_rag_indexed(project_id)
        res = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions",
            headers=headers,
            json={"prompt": "run the pipeline"},
        )
        assert res.status_code == 202, res.text
        detail = await api_client.get(
            f"/api/v1/projects/{project_id}", headers=headers
        )
        assert detail.json()["rag_gate"]["locked"] is False
        assert detail.json()["rag_gate"]["state"] == "complete"
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_compute_readiness_auto_enqueues_when_no_index(api_client) -> None:
    """No index + online → auto-enqueue the durable re-index job."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        project = await _load_project(project_id)
        rag_status: dict[str, Any] = {
            "chunks": 0,
            "indexing": False,
            "state": "idle",
            "progress": 0,
            "scanned_files": 0,
            "total_files": 0,
            "files_indexed": 0,
        }
        async with AsyncSessionLocal() as db:
            readiness = await compute_readiness(db, project, rag_status, True)
        assert readiness["state"] == GATE_STATE_INDEXING
        assert readiness["locked"] is True
        async with AsyncSessionLocal() as db:
            active = await active_reindex_job(db, project_id)
        assert active is not None
        assert active.status in ("PENDING", "RUNNING")
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_compute_readiness_unlocks_when_chunks_exist(api_client) -> None:
    """Observing an index flips rag_indexed_at and opens the gate."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        project = await _load_project(project_id)
        rag_status: dict[str, Any] = {
            "chunks": 12,
            "indexing": False,
            "state": "complete",
            "progress": 100,
            "scanned_files": 5,
            "total_files": 5,
            "files_indexed": 5,
            "finished_at": "2026-08-12 10:00:00",
        }
        async with AsyncSessionLocal() as db:
            readiness = await compute_readiness(db, project, rag_status, True)
        assert readiness["state"] == GATE_STATE_COMPLETE
        assert readiness["locked"] is False
        refreshed = await _load_project(project_id)
        assert refreshed.rag_indexed_at is not None
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_compute_readiness_offline_stays_locked(api_client) -> None:
    """Offline agents keep the gate locked without enqueuing a doomed job."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        project = await _load_project(project_id)
        async with AsyncSessionLocal() as db:
            readiness = await compute_readiness(db, project, None, False)
        assert readiness["state"] == GATE_STATE_OFFLINE
        assert readiness["locked"] is True
        async with AsyncSessionLocal() as db:
            active = await active_reindex_job(db, project_id)
        assert active is None
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_ensure_reindex_job_is_deduplicated(api_client) -> None:
    """Repeated ensure calls return the same in-flight job."""
    headers, project_id, user_id = await _create_user_project(api_client)
    try:
        async with AsyncSessionLocal() as db:
            first = await ensure_reindex_job(db, project_id, user_id)
            second = await ensure_reindex_job(db, project_id, user_id)
        assert first is not None and second is not None
        assert first.id == second.id
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_persisted_gate_state_transitions(api_client) -> None:
    """persisted_gate reports locked→complete as rag_indexed_at is set."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        project = await _load_project(project_id)
        assert persisted_gate(project)["locked"] is True
        async with AsyncSessionLocal() as db:
            attached = await db.get(Project, project_id)
            attached.rag_indexed_at = naive_utcnow()
            await db.commit()
        refreshed = await _load_project(project_id)
        gate = persisted_gate(refreshed)
        assert gate["locked"] is False
        assert gate["state"] == GATE_STATE_COMPLETE
    finally:
        await _delete_project(api_client, headers, project_id)
