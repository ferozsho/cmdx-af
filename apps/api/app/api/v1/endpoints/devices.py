"""Devices and Workstation Pairing Endpoints."""

import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.device_repo import DeviceRepository

router = APIRouter()


class DeviceResponse(BaseModel):
    """Registered device response schema."""

    id: str
    name: str
    hostname: str
    platform: str
    status: str
    agent_version: str = "0.1.0"
    os_version: str | None = None


@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)) -> Any:
    """Get all registered workstation devices from the database."""
    repo = DeviceRepository(db)
    devices = await repo.list_all()
    return [
        DeviceResponse(
            id=d.id,
            name=d.name,
            hostname=d.hostname,
            platform=d.platform,
            status=d.status,
            agent_version=d.agent_version,
            os_version=d.os_version,
        )
        for d in devices
    ]


@router.post("/devices/pairing-code")
async def generate_pairing_code() -> Any:
    """Generate temporary 8-character pairing code for Local Agent onboarding."""
    return {
        "pairing_code": f"AGF-{uuid.uuid4().hex[:4].upper()}",
        "expires_in_seconds": 600,
    }


@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Revoke a registered device: disconnect WSS and remove from DB."""
    from app.wss.connection_manager import wss_manager

    if wss_manager.is_device_online(device_id):
        await wss_manager.disconnect(device_id, db)

    repo = DeviceRepository(db)
    deleted = await repo.delete(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True, "detail": f"Device {device_id} revoked"}
