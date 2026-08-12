"""Evidence-backed responsible-AI control summary."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.approval import ApprovalRequest
from app.models.git_commit import GitCommit
from app.models.project import Project
from app.models.user import User
from app.models.verification_run import VerificationRun

router = APIRouter()


@router.get("/compliance/summary")
async def compliance_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return scoped control evidence without claiming external certification."""
    project_ids = select(Project.id).where(Project.user_id == current_user.id)
    approval_counts = await db.execute(
        select(ApprovalRequest.status, func.count(ApprovalRequest.id))
        .where(ApprovalRequest.user_id == current_user.id)
        .group_by(ApprovalRequest.status)
    )
    verification_counts = await db.execute(
        select(VerificationRun.status, func.count(VerificationRun.id))
        .where(VerificationRun.project_id.in_(project_ids))
        .group_by(VerificationRun.status)
    )
    provenance_count = await db.scalar(
        select(func.count(GitCommit.id)).where(
            GitCommit.project_id.in_(project_ids),
            GitCommit.ai_generated.is_(True),
            GitCommit.provenance_digest.is_not(None),
        )
    )
    return {
        "certification_status": "NOT_EXTERNALLY_CERTIFIED",
        "scope": "CURRENT_USER_PROJECTS",
        "controls": {
            "accountability": {
                "status": "IMPLEMENTED",
                "evidence": "owned instructions, agent runs, and approval decisions",
            },
            "human_oversight": {
                "status": "IMPLEMENTED",
                "approval_counts": {
                    status: int(count) for status, count in approval_counts.all()
                },
            },
            "traceability": {
                "status": "IMPLEMENTED",
                "ai_commits_with_provenance": int(provenance_count or 0),
            },
            "validation": {
                "status": "IMPLEMENTED",
                "verification_counts": {
                    status: int(count)
                    for status, count in verification_counts.all()
                },
            },
            "data_minimization": {
                "status": "IMPLEMENTED",
                "evidence": "bounded and secret-redacted LLM and command evidence",
            },
        },
        "alignment_note": (
            "These technical controls support transparency, accountability, "
            "traceability, and human oversight. Legal applicability and formal "
            "conformity assessment remain organization-specific."
        ),
    }
