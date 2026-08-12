"""Cloud-side device heartbeat persistence tests."""

import pytest

from app.core.database import AsyncSessionLocal
from app.repositories.device_repo import DeviceRepository

pytestmark = pytest.mark.asyncio


async def test_record_heartbeat_updates_liveness_and_workspace_ids() -> None:
    async with AsyncSessionLocal() as db:
        repo = DeviceRepository(db)
        device = await repo.create(
            name="Heartbeat Device",
            hostname="heartbeat-host",
            platform="linux",
        )
        original_last_seen = device.last_seen_at
        await db.commit()
        try:
            updated = await repo.record_heartbeat(
                device.id,
                ["workspace-b", "workspace-a", "workspace-a"],
            )
            await db.commit()

            assert updated is not None
            assert updated.status == "online"
            assert updated.last_seen_at >= original_last_seen
            assert updated.capabilities["workspace_ids"] == [
                "workspace-a",
                "workspace-b",
            ]
        finally:
            await repo.delete(device.id)
            await db.commit()
