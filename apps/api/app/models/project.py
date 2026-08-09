"""Project ORM Model."""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    """Development Project Model."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    execution_target: Mapped[str] = mapped_column(String, default="LOCAL")
    local_path: Mapped[str | None] = mapped_column(String, nullable=True)
    tech_stack: Mapped[dict] = mapped_column(JSON, default=dict)
    # ── Git authorization policies ──
    git_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    git_branch_patterns: Mapped[list] = mapped_column(
        JSON, default=lambda: ["*"], nullable=False
    )
    git_require_pr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    git_commit_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ── Filesystem CRUD access policies ──
    fs_read_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fs_write_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fs_delete_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_model: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="projects")
    workspaces = relationship("Workspace", back_populates="project")
    instructions = relationship(
        "Instruction", back_populates="project", cascade="all, delete-orphan"
    )
