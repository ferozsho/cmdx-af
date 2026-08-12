"""GitCommit ORM Model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import naive_utcnow


class GitCommit(Base):
    """Git commit log model."""

    __tablename__ = "git_commits"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    instruction_id: Mapped[str] = mapped_column(
        String, ForeignKey("instructions.id"), nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "projects.id",
            name="fk_git_commits_project_id_projects",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "users.id",
            name="fk_git_commits_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    commit_hash: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provenance_digest: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    prompt_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    changed_files: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    commit_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String, default="PENDING", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, nullable=False
    )
