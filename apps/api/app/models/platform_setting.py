"""Platform Setting ORM Model — DB-backed settings, including encrypted secrets."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import naive_utcnow


class PlatformSetting(Base):
    """A single platform setting value persisted in the database.

    Secret values (LLM API keys) are stored encrypted at rest; the plaintext
    is never written to the DB (see ``app.core.secrets``). Non-secret rows are
    also supported (``is_secret=False``) for future settings that should live
    in the DB instead of the runtime JSON file.
    """

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, onupdate=naive_utcnow, nullable=False
    )
