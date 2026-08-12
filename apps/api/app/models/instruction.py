"""Instruction ORM Model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import naive_utcnow


class Instruction(Base):
    """User Natural-Language Instruction Submission Model."""

    __tablename__ = "instructions"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_instructions_project_idempotency_key",
        ),
        Index("ix_instructions_queue", "status", "available_at", "created_at"),
        Index("ix_instructions_user_id", "user_id"),
        Index("ix_instructions_project_user", "project_id", "user_id"),
        Index("ix_instructions_session_id", "session_id"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "users.id",
            name="fk_instructions_user_id_users",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("sessions.id"), nullable=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    image_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, nullable=False
    )

    project = relationship("Project", back_populates="instructions")
    user = relationship("User")
    session = relationship("Session", back_populates="instructions")
    runs = relationship(
        "AgentRun",
        back_populates="instruction",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "InstructionEvent",
        back_populates="instruction",
        cascade="all, delete-orphan",
    )
