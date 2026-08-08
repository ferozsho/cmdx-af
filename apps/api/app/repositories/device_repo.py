"""Device database repository."""

from __future__ import annotations

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.user import User


class DeviceRepository:
    """Database operations for Device model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_default_user_id(self) -> str:
        """Resolve the default user ID (first user in DB)."""
        result = await self.db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user.id
        user = User(
            id=str(uuid.uuid4()),
            email="admin@agentforge.ai",
            hashed_password="auto-created-placeholder",
            full_name="Auto User",
        )
        self.db.add(user)
        await self.db.flush()
        return user.id

    async def list_all(self) -> List[Device]:
        """Return all registered devices."""
        result = await self.db.execute(
            select(Device).order_by(Device.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, device_id: str) -> Optional[Device]:
        """Get a single device by its primary key."""
        result = await self.db.execute(
            select(Device).where(Device.id == device_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        hostname: str,
        platform: str,
        user_id: str = "",
        os_version: str | None = None,
    ) -> Device:
        """Register a new device."""
        if not user_id:
            user_id = await self._get_default_user_id()
        device = Device(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            hostname=hostname,
            platform=platform,
            os_version=os_version,
            status="offline",
        )
        self.db.add(device)
        await self.db.flush()
        return device

    async def update_status(self, device_id: str, status: str) -> Optional[Device]:
        """Update device online/offline status."""
        device = await self.get_by_id(device_id)
        if device:
            device.status = status
            await self.db.flush()
        return device

    async def count(self) -> int:
        """Return total number of devices."""
        result = await self.db.execute(select(Device))
        return len(list(result.scalars().all()))

    async def count_online(self) -> int:
        """Return number of online devices."""
        result = await self.db.execute(
            select(Device).where(Device.status == "online")
        )
        return len(list(result.scalars().all()))

    async def delete(self, device_id: str) -> bool:
        """Delete a device by ID. Returns True if deleted."""
        device = await self.get_by_id(device_id)
        if device:
            await self.db.delete(device)
            await self.db.flush()
            return True
        return False
