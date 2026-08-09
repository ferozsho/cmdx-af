"""Session ORM Model — groups instructions into contextual sessions."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Session(Base):
    """A context session grouping related instructions together."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, default="New Session")
    model_name: Mapped[str] = mapped_column(String, default="deepseek-chat")
    context_limit: Mapped[int] = mapped_column(
        Integer, default=65536
    )  # max tokens for model
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    project = relationship("Project")
    user = relationship("User")
    instructions = relationship(
        "Instruction", back_populates="session", cascade="all, delete-orphan"
    )
