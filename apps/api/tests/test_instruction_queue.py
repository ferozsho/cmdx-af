"""Integration tests for durable instruction queue behavior."""

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

import app.worker as worker
from app.core.database import AsyncSessionLocal
from app.core.security import hash_device_token
from app.core.time import naive_utcnow
from app.main import app
from app.models.background_job import BackgroundJob
from app.models.instruction import Instruction
from app.models.instruction_event import InstructionEvent
from app.models.pairing_code import PairingCode

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api_client():
    """Return an ASGI-native authenticated-test client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def _create_user_project(
    api_client: httpx.AsyncClient,
    *,
    initial_instruction: str | None = None,
) -> tuple[dict[str, str], str, str]:
    """Register a unique user and create an owned project."""
    suffix = uuid.uuid4().hex
    registered = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"queue-{suffix}@mailinator.com",
            "password": "User@323123",
            "full_name": "Queue Test",
        },
    )
    assert registered.status_code == 201, registered.text
    auth = registered.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    body: dict[str, Any] = {"name": f"Queue Project {suffix}"}
    if initial_instruction:
        body["initial_instruction"] = initial_instruction
    created = await api_client.post(
        "/api/v1/projects",
        headers=headers,
        json=body,
    )
    assert created.status_code == 200, created.text
    return headers, created.json()["id"], auth["user"]["id"]


async def _delete_project(
    api_client: httpx.AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> None:
    deleted = await api_client.delete(
        f"/api/v1/projects/{project_id}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text


async def test_submission_is_idempotent_and_cancellable(api_client) -> None:
    """A retrying client receives one durable job and cancellation is idempotent."""
    headers, project_id, user_id = await _create_user_project(api_client)
    request_headers = {**headers, "Idempotency-Key": "queue-test-key"}
    try:
        first = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions",
            headers=request_headers,
            json={
                "prompt": "Perform a durable task",
                "image_bytes": "base64-test-data",
                "image_mime_type": "image/jpeg",
            },
        )
        duplicate = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions",
            headers=request_headers,
            json={"prompt": "Perform a durable task"},
        )
        assert first.status_code == duplicate.status_code == 202
        assert first.json()["id"] == duplicate.json()["id"]
        assert first.json()["status"] == "PENDING"
        assert first.json()["user_id"] == user_id

        instruction_id = first.json()["id"]
        cancelled = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions/{instruction_id}/cancel",
            headers=headers,
        )
        repeated = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions/{instruction_id}/cancel",
            headers=headers,
        )
        assert cancelled.status_code == repeated.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"
        assert repeated.json()["cancel_requested_at"] == cancelled.json()[
            "cancel_requested_at"
        ]

        async with AsyncSessionLocal() as db:
            instruction_count = await db.scalar(
                select(func.count(Instruction.id)).where(
                    Instruction.project_id == project_id
                )
            )
            events = await db.scalars(
                select(InstructionEvent).where(
                    InstructionEvent.instruction_id == instruction_id
                )
            )
        assert instruction_count == 1
        async with AsyncSessionLocal() as db:
            stored_instruction = await db.get(Instruction, instruction_id)
        assert stored_instruction is not None
        assert stored_instruction.image_mime_type == "image/jpeg"
        assert [event.payload["status"] for event in events.all()] == [
            "PENDING",
            "CANCEL_REQUESTED",
        ]
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_pairing_code_is_hashed_durable_and_one_time(api_client) -> None:
    """Pairing survives process boundaries without storing or replaying raw codes."""
    headers, project_id, _ = await _create_user_project(api_client)
    device_id = None
    try:
        generated = await api_client.post(
            "/api/v1/devices/pairing-code",
            headers=headers,
        )
        assert generated.status_code == 200, generated.text
        raw_code = generated.json()["pairing_code"]
        assert len(raw_code) == 8
        assert raw_code.isalnum()
        assert raw_code == raw_code.upper()

        async with AsyncSessionLocal() as db:
            stored = await db.scalar(
                select(PairingCode).where(
                    PairingCode.code_hash == hash_device_token(raw_code)
                )
            )
        assert stored is not None
        assert stored.code_hash != raw_code

        payload = {
            "pairing_code": raw_code,
            "device_name": "Queue Test Device",
            "hostname": "queue-test-host",
            "platform": "linux",
        }
        paired = await api_client.post("/api/v1/devices/pair", json=payload)
        assert paired.status_code == 200, paired.text
        device_id = paired.json()["device_id"]
        assert paired.json()["device_token"].startswith("dtk_")

        replay = await api_client.post("/api/v1/devices/pair", json=payload)
        assert replay.status_code == 400
        async with AsyncSessionLocal() as db:
            consumed = await db.get(PairingCode, stored.id)
        assert consumed is not None
        assert consumed.used_at is not None
    finally:
        if device_id:
            revoked = await api_client.delete(
                f"/api/v1/devices/{device_id}",
                headers=headers,
            )
            assert revoked.status_code == 200, revoked.text
        await _delete_project(api_client, headers, project_id)


async def test_initial_instruction_uses_durable_queue(api_client) -> None:
    """Project creation queues initial work without an in-process task."""
    headers, project_id, user_id = await _create_user_project(
        api_client,
        initial_instruction="Start from the durable queue",
    )
    try:
        async with AsyncSessionLocal() as db:
            instruction = await db.scalar(
                select(Instruction).where(Instruction.project_id == project_id)
            )
            event = await db.scalar(
                select(InstructionEvent).where(
                    InstructionEvent.project_id == project_id
                )
            )
        assert instruction is not None
        assert instruction.user_id == user_id
        assert instruction.status == "PENDING"
        assert event is not None
        assert event.payload["status"] == "PENDING"
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_rag_reindex_is_durable_and_deduplicated(
    api_client,
    monkeypatch,
) -> None:
    """RAG indexing is persisted, deduplicated, and completed by the worker."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        first = await api_client.post(
            f"/api/v1/projects/{project_id}/rag/reindex",
            headers=headers,
        )
        duplicate = await api_client.post(
            f"/api/v1/projects/{project_id}/rag/reindex",
            headers=headers,
        )
        assert first.status_code == duplicate.status_code == 200
        assert first.json()["status"] == "started"
        assert duplicate.json()["status"] == "running"
        job_id = first.json()["job"]["id"]
        assert duplicate.json()["job"]["id"] == job_id

        async with AsyncSessionLocal() as db:
            job = await db.get(BackgroundJob, job_id)
            assert job is not None
            job.created_at = datetime(2000, 1, 1)
            job.available_at = datetime(2000, 1, 1)
            await db.commit()

        claimed = await worker._claim_background_job()
        assert claimed is not None
        assert claimed["id"] == job_id

        async def successful_reindex(**kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(
                success=True,
                result={
                    "files_indexed": 12,
                    "chunks": 34,
                    "last_index": "2026-08-11T00:00:00Z",
                },
                error=None,
            )

        monkeypatch.setattr(
            worker.ToolGateway,
            "invoke_tool",
            successful_reindex,
        )
        await worker._handle_background_job(claimed)

        status = await api_client.get(
            f"/api/v1/projects/{project_id}/rag/reindex-status",
            headers=headers,
        )
        assert status.status_code == 200, status.text
        assert status.json()["status"] == "done"
        assert status.json()["job"]["files_indexed"] == 12
        assert status.json()["job"]["chunks"] == 34
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_worker_claims_and_retries_failed_job(api_client, monkeypatch) -> None:
    """A failed attempt is delayed and retried up to the configured limit."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        queued = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions",
            headers=headers,
            json={"prompt": "Exercise worker retry"},
        )
        assert queued.status_code == 202, queued.text
        instruction_id = queued.json()["id"]
        async with AsyncSessionLocal() as db:
            instruction = await db.get(Instruction, instruction_id)
            assert instruction is not None
            instruction.created_at = datetime(2000, 1, 1)
            instruction.available_at = datetime(2000, 1, 1)
            await db.commit()

        job = await worker._claim_instruction()
        assert job is not None
        assert job["id"] == instruction_id
        assert job["attempt_count"] == 1

        class FailedPipeline:
            def __init__(self, project_id: str) -> None:
                self.project_id = project_id

            async def run_pipeline(self, *args: Any, **kwargs: Any) -> dict:
                return {
                    "status": "FAILED",
                    "final_context": {"pipeline_error": "planned failure"},
                }

        monkeypatch.setattr(worker, "PipelineOrchestrator", FailedPipeline)
        before_retry = naive_utcnow()
        await worker._handle_job(job)

        async with AsyncSessionLocal() as db:
            instruction = await db.get(Instruction, instruction_id)
            retry_event = await db.scalar(
                select(InstructionEvent)
                .where(
                    InstructionEvent.instruction_id == instruction_id,
                    InstructionEvent.payload["status"].as_string()
                    == "RETRYING",
                )
                .order_by(InstructionEvent.id.desc())
            )
        assert instruction is not None
        assert instruction.status == "PENDING"
        assert instruction.attempt_count == 1
        assert instruction.available_at > before_retry
        assert instruction.last_error == "planned failure"
        assert retry_event is not None
    finally:
        await _delete_project(api_client, headers, project_id)


async def test_stale_job_with_missing_heartbeat_is_recovered(api_client) -> None:
    """Legacy or crashed RUNNING rows are requeued even without a heartbeat."""
    headers, project_id, _ = await _create_user_project(api_client)
    try:
        queued = await api_client.post(
            f"/api/v1/projects/{project_id}/instructions",
            headers=headers,
            json={"prompt": "Recover this job"},
        )
        instruction_id = queued.json()["id"]
        async with AsyncSessionLocal() as db:
            instruction = await db.get(Instruction, instruction_id)
            assert instruction is not None
            instruction.status = "RUNNING"
            instruction.started_at = naive_utcnow() - timedelta(hours=1)
            instruction.heartbeat_at = None
            await db.commit()

        assert await worker._recover_stale_jobs() >= 1
        async with AsyncSessionLocal() as db:
            instruction = await db.get(Instruction, instruction_id)
        assert instruction is not None
        assert instruction.status == "PENDING"
        assert "heartbeat expired" in (instruction.last_error or "")
    finally:
        await _delete_project(api_client, headers, project_id)
