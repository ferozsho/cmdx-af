"""Durable project event emitted during instruction execution."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import naive_utcnow


class InstructionEvent(Base):
    """Replayable event for cross-process progress streaming."""

    __tablename__ = "instruction_events"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instruction_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=naive_utcnow,
        nullable=False,
    )
    instruction = relationship("Instruction", back_populates="events")
