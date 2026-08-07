"""AgentTemplate ORM Model — versioned agent definitions."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, JSON, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AgentTemplate(Base):
    """Versioned agent definition template."""

    __tablename__ = "agent_templates"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capability: Mapped[str] = mapped_column(
        String(50), default="reasoning", nullable=False
    )
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    versions = relationship(
        "AgentVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="AgentVersion.version.desc()",
    )
    project_configs = relationship(
        "ProjectAgent", back_populates="template", cascade="all, delete-orphan"
    )


class AgentVersion(Base):
    """Immutable version snapshot of an agent template."""

    __tablename__ = "agent_versions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    template_id: Mapped[str] = mapped_column(
        String, ForeignKey("agent_templates.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    template = relationship("AgentTemplate", back_populates="versions")


class ProjectAgent(Base):
    """Per-project agent configuration — links templates to projects with overrides."""

    __tablename__ = "project_agents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id"), nullable=False
    )
    template_id: Mapped[str] = mapped_column(
        String, ForeignKey("agent_templates.id"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    custom_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    template = relationship("AgentTemplate", back_populates="project_configs")
