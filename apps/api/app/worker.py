"""Durable database-backed worker for instruction pipelines."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any

from sqlalchemy import or_, select, update

from app.agents.pipeline import PipelineOrchestrator
from app.core.config import (
    DEFAULT_RAG_CHUNK_OVERLAP,
    DEFAULT_RAG_CHUNK_SIZE,
    get_setting,
)
from app.core.database import AsyncSessionLocal
from app.llm.router import LLMConfigurationError
from app.models.background_job import BackgroundJob
from app.models.device import Device
from app.models.instruction import Instruction
from app.models.session import Session
from app.models.workspace import Workspace
from app.repositories.device_repo import DeviceRepository
from app.services.instruction_events import append_instruction_event
from app.services.platform_settings import load_db_secrets
from app.tools.gateway.tool_gateway import ToolGateway

logger = logging.getLogger(__name__)

POLL_SECONDS = 1.0
STALE_AFTER_SECONDS = 300
RECOVERY_INTERVAL_SECONDS = 60
DEFAULT_WORKSPACE = "ws-test"


async def _recover_stale_jobs() -> int:
    """Return abandoned RUNNING jobs to the queue after a worker failure."""
    stale_before = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=STALE_AFTER_SECONDS)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Instruction)
            .where(
                Instruction.status == "RUNNING",
                or_(
                    Instruction.heartbeat_at < stale_before,
                    (
                        Instruction.heartbeat_at.is_(None)
                        & Instruction.started_at.is_not(None)
                        & (Instruction.started_at < stale_before)
                    ),
                    (
                        Instruction.heartbeat_at.is_(None)
                        & Instruction.started_at.is_(None)
                        & (Instruction.created_at < stale_before)
                    ),
                ),
            )
            .values(
                status="PENDING",
                available_at=datetime.now(UTC).replace(tzinfo=None),
                last_error="Recovered after worker heartbeat expired.",
            )
        )
        background_result = await db.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.status == "RUNNING",
                or_(
                    BackgroundJob.heartbeat_at < stale_before,
                    (
                        BackgroundJob.heartbeat_at.is_(None)
                        & BackgroundJob.started_at.is_not(None)
                        & (BackgroundJob.started_at < stale_before)
                    ),
                ),
            )
            .values(
                status="PENDING",
                available_at=datetime.now(UTC).replace(tzinfo=None),
                last_error="Recovered after worker heartbeat expired.",
            )
        )
        await db.commit()
        return int(result.rowcount or 0) + int(background_result.rowcount or 0)


async def _claim_instruction() -> dict[str, Any] | None:
    """Atomically claim the next eligible job across concurrent workers."""
    now = datetime.now(UTC).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                select(Instruction)
                .where(
                    Instruction.status == "PENDING",
                    Instruction.available_at <= now,
                )
                .order_by(Instruction.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            instruction = result.scalar_one_or_none()
            if instruction is None:
                return None
            if instruction.cancel_requested_at is not None:
                instruction.status = "CANCELLED"
                instruction.finished_at = now
                await append_instruction_event(
                    instruction.project_id,
                    instruction.id,
                    {
                        "instruction_id": instruction.id,
                        "agent_name": "System",
                        "status": "CANCELLED",
                        "message": "Instruction cancelled before execution.",
                    },
                    db,
                )
                return None
            instruction.status = "RUNNING"
            instruction.attempt_count += 1
            instruction.started_at = instruction.started_at or now
            instruction.heartbeat_at = now
            instruction.last_error = None
            return {
                "id": instruction.id,
                "project_id": instruction.project_id,
                "user_id": instruction.user_id,
                "session_id": instruction.session_id,
                "prompt": instruction.prompt,
                "image_data": instruction.image_data,
                "image_mime_type": instruction.image_mime_type,
                "attempt_count": instruction.attempt_count,
                "max_attempts": instruction.max_attempts,
            }


async def _resolve_target(job: dict[str, Any]) -> tuple[str, str]:
    """Resolve an owned device and authorized workspace registry ID."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workspace)
            .join(Device, Device.id == Workspace.device_id)
            .where(
                Workspace.project_id == job["project_id"],
                Device.user_id == job["user_id"],
            )
            .limit(1)
        )
        workspace = result.scalar_one_or_none()
        if workspace:
            return workspace.device_id, workspace.id
        devices = await DeviceRepository(db).list_for_user(job["user_id"])
        return (devices[0].id if devices else ""), DEFAULT_WORKSPACE


async def _claim_background_job() -> dict[str, Any] | None:
    """Atomically claim one eligible durable control-plane job."""
    now = datetime.now(UTC).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            job = await db.scalar(
                select(BackgroundJob)
                .where(
                    BackgroundJob.status == "PENDING",
                    BackgroundJob.available_at <= now,
                )
                .order_by(BackgroundJob.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if not job:
                return None
            job.status = "RUNNING"
            job.attempt_count += 1
            job.started_at = job.started_at or now
            job.heartbeat_at = now
            job.last_error = None
            return {
                "id": job.id,
                "project_id": job.project_id,
                "user_id": job.user_id,
                "job_type": job.job_type,
                "payload": job.payload,
            }


async def _handle_background_job(job: dict[str, Any]) -> None:
    """Execute a claimed control-plane job and apply retry policy."""
    device_id, workspace_id = await _resolve_target(job)
    result_data: dict | None = None
    error: str | None = None
    try:
        if job["job_type"] != "RAG_REINDEX":
            raise ValueError(f"Unsupported background job: {job['job_type']}")
        tool_result = await ToolGateway.invoke_tool(
            device_id=device_id,
            workspace_id=workspace_id,
            job_id=job["id"],
            tool_name="rag_reindex",
            arguments={
                "chunk_size": int(
                    get_setting("RAG_CHUNK_SIZE", DEFAULT_RAG_CHUNK_SIZE)
                ),
                "chunk_overlap": int(
                    get_setting(
                        "RAG_CHUNK_OVERLAP",
                        DEFAULT_RAG_CHUNK_OVERLAP,
                    )
                ),
            },
        )
        if not tool_result.success:
            raise RuntimeError(tool_result.error or "RAG re-index failed")
        raw_result = (
            tool_result.result if isinstance(tool_result.result, dict) else {}
        )
        result_data = {
            "files_indexed": int(raw_result.get("files_indexed") or 0),
            "chunks": int(raw_result.get("chunks") or 0),
            "last_index": raw_result.get("last_index"),
        }
    except Exception as exc:
        logger.exception("Background job failed: %s", job["id"])
        error = f"{type(exc).__name__}: {exc}"

    now = datetime.now(UTC).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        stored = await db.get(BackgroundJob, job["id"])
        if not stored:
            return
        if error is None:
            stored.status = "COMPLETED"
            stored.result_data = result_data
            stored.finished_at = now
        elif stored.attempt_count < stored.max_attempts:
            delay_seconds = min(60, 5 * (2 ** (stored.attempt_count - 1)))
            stored.status = "PENDING"
            stored.available_at = now + timedelta(seconds=delay_seconds)
            stored.last_error = error
        else:
            stored.status = "FAILED"
            stored.finished_at = now
            stored.last_error = error
        stored.heartbeat_at = now
        await db.commit()


async def _load_session_context(
    job: dict[str, Any],
) -> tuple[list[dict], str | None, int | None]:
    """Load bounded context for the job's owned session."""
    if not job["session_id"]:
        return [], None, None
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, job["session_id"])
        if (
            not session
            or session.project_id != job["project_id"]
            or session.user_id != job["user_id"]
        ):
            return [], None, None
        result = await db.execute(
            select(Instruction)
            .where(
                Instruction.session_id == session.id,
                Instruction.id != job["id"],
                Instruction.status.in_(["COMPLETED", "FAILED"]),
            )
            .order_by(Instruction.created_at.desc())
            .limit(5)
        )
        previous = list(reversed(result.scalars().all()))
        return (
            [
                {
                    "instruction_id": item.id,
                    "prompt": item.prompt,
                    "status": item.status,
                }
                for item in previous
            ],
            session.model_name,
            session.context_limit,
        )


async def _is_cancel_requested(instruction_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        instruction = await db.get(Instruction, instruction_id)
        return bool(instruction and instruction.cancel_requested_at)


async def _handle_job(job: dict[str, Any]) -> None:
    """Execute a claimed job and transition it to a terminal or retry state."""
    device_id, workspace_id = await _resolve_target(job)
    previous, model_name, context_limit = await _load_session_context(job)

    async def event_callback(
        agent_name: str,
        status: str,
        message: str,
        data: dict | None = None,
    ) -> None:
        payload = {
            "instruction_id": job["id"],
            "agent_name": agent_name,
            "status": status,
            "message": message,
        }
        if data:
            payload["data"] = data
        async with AsyncSessionLocal() as db:
            instruction = await db.get(Instruction, job["id"])
            if instruction:
                instruction.heartbeat_at = datetime.now(UTC).replace(tzinfo=None)
            await append_instruction_event(
                job["project_id"],
                job["id"],
                payload,
                db,
            )
            await db.commit()

    orchestrator = PipelineOrchestrator(project_id=job["project_id"])
    retryable = True
    try:
        result = await orchestrator.run_pipeline(
            job["id"],
            job["prompt"],
            event_callback=event_callback,
            device_id=device_id,
            workspace_id=workspace_id,
            image_bytes=job["image_data"],
            image_mime_type=job["image_mime_type"],
            previous_context=previous,
            session_model_name=model_name,
            session_context_limit=context_limit,
            cancel_check=lambda: _is_cancel_requested(job["id"]),
            user_id=job["user_id"],
        )
        status = result["status"]
        error = result.get("final_context", {}).get("pipeline_error")
    except Exception as exc:
        logger.exception("Unhandled instruction worker failure: %s", job["id"])
        status = "FAILED"
        error = f"{type(exc).__name__}: {exc}"
        retryable = not isinstance(exc, LLMConfigurationError)

    now = datetime.now(UTC).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        instruction = await db.get(Instruction, job["id"])
        if not instruction:
            return
        if instruction.cancel_requested_at or status == "CANCELLED":
            instruction.status = "CANCELLED"
            instruction.finished_at = now
            final_status = "CANCELLED"
            message = "Instruction cancelled."
        elif status == "COMPLETED":
            instruction.status = "COMPLETED"
            instruction.finished_at = now
            instruction.last_error = None
            final_status = "COMPLETED"
            message = "Instruction completed."
        elif status == "WAITING_APPROVAL":
            instruction.status = "WAITING_APPROVAL"
            instruction.last_error = error or "Human approval required."
            final_status = "WAITING_APPROVAL"
            message = "Instruction paused for human approval."
        elif retryable and instruction.attempt_count < instruction.max_attempts:
            delay_seconds = min(60, 5 * (2 ** (instruction.attempt_count - 1)))
            instruction.status = "PENDING"
            instruction.available_at = now + timedelta(seconds=delay_seconds)
            instruction.last_error = error or "Pipeline attempt failed."
            final_status = "RETRYING"
            message = f"Retry scheduled in {delay_seconds} seconds."
        else:
            instruction.status = "FAILED"
            instruction.finished_at = now
            instruction.last_error = error or "Pipeline failed."
            final_status = "FAILED"
            message = (
                "Instruction cannot run until its LLM provider is configured."
                if not retryable
                else "Instruction failed after all retry attempts."
            )
        instruction.heartbeat_at = now
        await append_instruction_event(
            job["project_id"],
            job["id"],
            {
                "instruction_id": job["id"],
                "agent_name": "System",
                "status": final_status,
                "message": message,
                "attempt": instruction.attempt_count,
            },
            db,
        )
        await db.commit()


async def run_worker() -> None:
    """Poll forever, recovering stale jobs and processing claimed work."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Load DB-backed API keys so the pipeline's LLM router can resolve them.
    await load_db_secrets()
    recovered = await _recover_stale_jobs()
    if recovered:
        logger.warning("Recovered %d stale instruction jobs", recovered)
    logger.info("Instruction worker started")
    last_recovery = monotonic()
    while True:
        if monotonic() - last_recovery >= RECOVERY_INTERVAL_SECONDS:
            recovered = await _recover_stale_jobs()
            if recovered:
                logger.warning("Recovered %d stale instruction jobs", recovered)
            last_recovery = monotonic()
        job = await _claim_instruction()
        if job is None:
            background_job = await _claim_background_job()
            if background_job is None:
                await asyncio.sleep(POLL_SECONDS)
                continue
            await _handle_background_job(background_job)
        else:
            await _handle_job(job)


if __name__ == "__main__":
    asyncio.run(run_worker())
