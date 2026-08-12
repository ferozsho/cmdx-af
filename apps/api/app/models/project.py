"""Project ORM Model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import naive_utcnow


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
    ci_gate_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    git_commit_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ── Filesystem CRUD access policies ──
    fs_read_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fs_write_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fs_delete_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approval_mode: Mapped[str] = mapped_column(
        String,
        default="RISKY",
        nullable=False,
    )
    command_allowlist: Mapped[list] = mapped_column(
        JSON,
        default=lambda: [
            "pytest",
            "npm",
            "pnpm",
            "yarn",
            "ruff",
            "mypy",
            "eslint",
            "tsc",
            "python",
            "node",
        ],
        nullable=False,
    )
    max_command_seconds: Mapped[int] = mapped_column(
        Integer,
        default=120,
        nullable=False,
    )
    default_model: Mapped[str | None] = mapped_column(String, nullable=True)
    # ── RAG readiness gate ──
    # Set once a successful RAG index exists. NULL means the project has no
    # index yet, so project content access is gated (423) until the first
    # index completes. Subsequent re-indexes do not re-lock the project.
    rag_indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, onupdate=naive_utcnow, nullable=False
    )

    user = relationship("User", back_populates="projects")
    workspaces = relationship("Workspace", back_populates="project")
    instructions = relationship(
        "Instruction", back_populates="project", cascade="all, delete-orphan"
    )
    background_jobs = relationship(
        "BackgroundJob",
        back_populates="project",
        cascade="all, delete-orphan",
    )
