"""RAG readiness gate: auto re-index and project access gating.

A project is considered RAG-ready once an index exists (persisted in
``projects.rag_indexed_at``). Until then, project content endpoints return
423 Locked and the UI shows an indexing gate screen.

Readiness is resolved lazily: the readiness endpoint / RAG stats call
``rag_status`` on the local agent, auto-enqueue a durable ``RAG_REINDEX``
background job when no index exists, and flip ``rag_indexed_at`` the moment
an index is observed. The worker sweep re-enqueues for any project still
missing an index, so recovery is automatic even if the agent was offline.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import naive_utcnow
from app.models.background_job import BackgroundJob
from app.models.project import Project

logger = logging.getLogger(__name__)

RAG_REINDEX_JOB_TYPE = "RAG_REINDEX"
_ACTIVE_JOB_STATUSES = ("PENDING", "RUNNING")

GATE_STATE_COMPLETE = "complete"
GATE_STATE_INDEXING_REQUIRED = "indexing_required"
GATE_STATE_INDEXING = "indexing"
GATE_STATE_FAILED = "failed"
GATE_STATE_OFFLINE = "offline"


def persisted_gate(project: Project) -> Dict[str, Any]:
    """DB-only gate state (no tool call) for list/detail responses."""
    indexed_at = project.rag_indexed_at
    if indexed_at is not None:
        return {
            "state": GATE_STATE_COMPLETE,
            "locked": False,
            "indexed_at": indexed_at.isoformat() if indexed_at else None,
        }
    return {
        "state": GATE_STATE_INDEXING_REQUIRED,
        "locked": True,
        "indexed_at": None,
    }


def gate_http_exception(project: Project) -> HTTPException:
    """Build a 423 Locked response with a structured rag_gate payload."""
    return HTTPException(
        status_code=423,
        detail={
            "error": "RAG indexing required before this project can be used.",
            "rag_gate": persisted_gate(project),
        },
    )


async def latest_reindex_job(
    db: AsyncSession, project_id: str
) -> Optional[BackgroundJob]:
    """Return the most recent RAG_REINDEX job for a project (or None)."""
    return await db.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.project_id == project_id,
            BackgroundJob.job_type == RAG_REINDEX_JOB_TYPE,
        )
        .order_by(BackgroundJob.created_at.desc())
        .limit(1)
    )


async def active_reindex_job(
    db: AsyncSession, project_id: str
) -> Optional[BackgroundJob]:
    """Return an in-flight RAG_REINDEX job (PENDING/RUNNING) or None."""
    return await db.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.project_id == project_id,
            BackgroundJob.job_type == RAG_REINDEX_JOB_TYPE,
            BackgroundJob.status.in_(_ACTIVE_JOB_STATUSES),
        )
        .order_by(BackgroundJob.created_at.desc())
        .limit(1)
    )


async def ensure_reindex_job(
    db: AsyncSession, project_id: str, user_id: str
) -> Optional[BackgroundJob]:
    """Durably enqueue a RAG_REINDEX job for a project (deduplicated)."""
    existing = await active_reindex_job(db, project_id)
    if existing:
        return existing
    job = BackgroundJob(
        project_id=project_id,
        user_id=user_id,
        job_type=RAG_REINDEX_JOB_TYPE,
        status="PENDING",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


def job_payload(job: Optional[BackgroundJob]) -> Optional[Dict[str, Any]]:
    """Serialize the latest re-index job for readiness/reindex responses."""
    if job is None:
        return None
    result = job.result_data or {}
    public_status = {
        "PENDING": "running",
        "RUNNING": "running",
        "COMPLETED": "done",
        "FAILED": "failed",
    }.get(job.status, job.status.lower())
    return {
        "id": job.id,
        "status": public_status,
        "files_indexed": int(result.get("files_indexed") or 0),
        "chunks": int(result.get("chunks") or 0),
        "last_index": result.get("last_index"),
        "error": job.last_error,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": (
            job.finished_at.isoformat() if job.finished_at else None
        ),
    }


async def compute_readiness(
    db: AsyncSession,
    project: Project,
    rag_status: Optional[Dict[str, Any]],
    online: bool,
) -> Dict[str, Any]:
    """Resolve readiness from rag_status + jobs, auto-enqueue when needed.

    ``rag_status`` is the parsed ``rag_status`` tool result (or None when the
    local agent is unreachable). May persist ``rag_indexed_at`` (unlock) and
    enqueue a RAG_REINDEX job (auto re-index) as side effects.
    """
    indexed_at = project.rag_indexed_at
    if indexed_at is not None:
        return {
            "state": GATE_STATE_COMPLETE,
            "locked": False,
            "online": online,
            "indexing": False,
            "progress": 0.0,
            "files_scanned": 0,
            "total_files": 0,
            "files_indexed": (
                int(rag_status.get("files_indexed") or 0)
                if rag_status else 0
            ),
            "chunks": int(rag_status.get("chunks") or 0) if rag_status else 0,
            "current_file": None,
            "last_index": (
                rag_status.get("finished_at") if rag_status else None
            ),
            "indexed_at": indexed_at.isoformat() if indexed_at else None,
            "job": None,
        }

    # Bind the project instance to this session so mutations below persist.
    project = await db.get(Project, project.id) or project

    chunks = int((rag_status or {}).get("chunks") or 0)
    indexing = bool((rag_status or {}).get("indexing"))
    active = await active_reindex_job(db, project.id)
    latest = await latest_reindex_job(db, project.id)
    latest_failed = (
        latest is not None
        and latest.status == "FAILED"
        and active is None
    )

    if not online:
        state = GATE_STATE_OFFLINE
    elif indexing or active is not None:
        state = GATE_STATE_INDEXING
    elif chunks > 0:
        # First observed index → unlock the project permanently.
        project.rag_indexed_at = naive_utcnow()
        await db.commit()
        state = GATE_STATE_COMPLETE
    elif latest_failed:
        state = GATE_STATE_FAILED
    else:
        # No index and nothing running → auto-enqueue the re-index process.
        try:
            await ensure_reindex_job(db, project.id, project.user_id)
        except Exception:
            logger.exception("Failed to auto-enqueue RAG re-index")
        state = GATE_STATE_INDEXING

    return {
        "state": state,
        "locked": state != GATE_STATE_COMPLETE,
        "online": online,
        "indexing": indexing or active is not None,
        "progress": float((rag_status or {}).get("progress") or 0),
        "files_scanned": int((rag_status or {}).get("scanned_files") or 0),
        "total_files": int((rag_status or {}).get("total_files") or 0),
        "files_indexed": int((rag_status or {}).get("files_indexed") or 0),
        "chunks": chunks,
        "current_file": (rag_status or {}).get("current_file"),
        "last_index": (rag_status or {}).get("finished_at"),
        "indexed_at": (
            project.rag_indexed_at.isoformat()
            if project.rag_indexed_at else None
        ),
        "job": job_payload(latest),
    }
