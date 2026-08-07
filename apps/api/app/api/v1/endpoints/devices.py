"""Devices and Workstation Pairing Endpoints."""

import uuid
from typing import Any, List

from fastapi import APIRouter, Depends
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
