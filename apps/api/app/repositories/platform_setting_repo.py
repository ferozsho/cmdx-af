"""PlatformSetting database repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import naive_utcnow
from app.models.platform_setting import PlatformSetting


class PlatformSettingRepository:
    """Database operations for the ``platform_settings`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, key: str) -> Optional[PlatformSetting]:
        """Fetch a single setting by key."""
        return await self.db.get(PlatformSetting, key)

    async def list_secrets(self) -> list[PlatformSetting]:
        """Return all secret-flagged rows (for the in-memory cache load)."""
        result = await self.db.execute(
            select(PlatformSetting).where(
                PlatformSetting.is_secret.is_(True)
            )
        )
        return list(result.scalars().all())

    async def upsert(
        self, key: str, value: str, is_secret: bool = False
    ) -> PlatformSetting:
        """Insert or update a setting value."""
        row = await self.db.get(PlatformSetting, key)
        if row is None:
            row = PlatformSetting(
                key=key,
                value=value,
                is_secret=is_secret,
                updated_at=naive_utcnow(),
            )
            self.db.add(row)
        else:
            row.value = value
            row.is_secret = is_secret
            row.updated_at = naive_utcnow()
        return row

    async def delete(self, key: str) -> bool:
        """Remove a setting row; returns True if a row was deleted."""
        row = await self.db.get(PlatformSetting, key)
        if row is None:
            return False
        await self.db.delete(row)
        return True
