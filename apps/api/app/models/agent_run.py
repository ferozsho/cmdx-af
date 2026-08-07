"""AgentRun ORM Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AgentRun(Base):
    """Execution step log model for an agent in a pipeline."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    instruction_id: Mapped[str] = mapped_column(
        String, ForeignKey("instructions.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    instruction = relationship("Instruction", back_populates="runs")
