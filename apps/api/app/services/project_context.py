"""Bounded project knowledge for tech-lead and IDE/MCP consumers."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.approval import ApprovalRequest
from app.models.artifact import Artifact
from app.models.git_commit import GitCommit
from app.models.instruction import Instruction
from app.models.project import Project
from app.models.verification_run import VerificationRun


async def build_project_context(
    db: AsyncSession,
    project: Project,
    *,
    include_artifact_content: bool = False,
) -> dict[str, Any]:
    """Return recent durable project state with strict count and size bounds."""
    instructions = (
        await db.scalars(
            select(Instruction)
            .where(Instruction.project_id == project.id)
            .order_by(Instruction.created_at.desc())
            .limit(20)
        )
    ).all()
    instruction_ids = [instruction.id for instruction in instructions]
    runs = (
        await db.scalars(
            select(AgentRun)
            .where(AgentRun.instruction_id.in_(instruction_ids or [""]))
            .order_by(AgentRun.created_at.desc())
            .limit(50)
        )
    ).all()
    artifacts = (
        await db.scalars(
            select(Artifact)
            .where(Artifact.instruction_id.in_(instruction_ids or [""]))
            .order_by(Artifact.created_at.desc())
            .limit(20)
        )
    ).all()
    verifications = (
        await db.scalars(
            select(VerificationRun)
            .where(VerificationRun.project_id == project.id)
            .order_by(VerificationRun.created_at.desc())
            .limit(30)
        )
    ).all()
    commits = (
        await db.scalars(
            select(GitCommit)
            .where(GitCommit.project_id == project.id)
            .order_by(GitCommit.created_at.desc())
            .limit(20)
        )
    ).all()
    approvals = (
        await db.scalars(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.project_id == project.id,
                ApprovalRequest.status == "PENDING",
            )
            .order_by(ApprovalRequest.requested_at.desc())
            .limit(20)
        )
    ).all()
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "tech_stack": project.tech_stack,
            "execution_target": project.execution_target,
        },
        "instructions": [
            {
                "id": item.id,
                "prompt": item.prompt[:2000],
                "status": item.status,
                "last_error": (item.last_error or "")[:1000] or None,
                "created_at": item.created_at.isoformat(),
            }
            for item in instructions
        ],
        "agent_runs": [
            {
                "instruction_id": item.instruction_id,
                "agent": item.agent_name,
                "status": item.status,
                "duration_seconds": item.duration_seconds,
            }
            for item in runs
        ],
        "artifacts": [
            {
                "instruction_id": item.instruction_id,
                "title": item.title,
                "type": item.artifact_type,
                **(
                    {"content": item.content[:6000]}
                    if include_artifact_content
                    else {}
                ),
            }
            for item in artifacts
        ],
        "verifications": [
            {
                "instruction_id": item.instruction_id,
                "category": item.category,
                "status": item.status,
                "duration_seconds": item.duration_seconds,
                "evidence_sha256": item.output_digest,
            }
            for item in verifications
        ],
        "commits": [
            {
                "instruction_id": item.instruction_id,
                "hash": item.commit_hash,
                "branch": item.branch,
                "verification_status": item.verification_status,
                "provenance_sha256": item.provenance_digest,
            }
            for item in commits
        ],
        "questions": [
            {
                "approval_id": item.id,
                "instruction_id": item.instruction_id,
                "summary": item.summary,
                "risk": item.risk_level,
                "expires_at": item.expires_at.isoformat(),
            }
            for item in approvals
        ],
    }
