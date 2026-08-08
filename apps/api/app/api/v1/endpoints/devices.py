"""Devices and Workstation Pairing Endpoints."""

import time
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.device_repo import DeviceRepository

router = APIRouter()

# Temporary pairing codes: code -> {created_at, expires_at}
_pairing_codes: Dict[str, Dict[str, float]] = {}
_PAIRING_TTL_SECONDS = 600


class DeviceResponse(BaseModel):
    """Registered device response schema."""

    id: str
    name: str
    hostname: str
    platform: str
    status: str
    agent_version: str = "0.1.0"
    os_version: str | None = None


class PairRequest(BaseModel):
    """Device pairing exchange request (from local agent)."""

    pairing_code: str
    device_name: str = ""
    hostname: str = ""
    platform: str = "unknown"
    os_version: str | None = None


class TokenValidateRequest(BaseModel):
    """Device token validation request."""

    device_id: str
    device_token: str


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
    """Generate and store a temporary pairing code for Local Agent onboarding."""
    code = f"AGF-{uuid.uuid4().hex[:4].upper()}"
    now = time.time()
    _pairing_codes[code] = {
        "created_at": now,
        "expires_at": now + _PAIRING_TTL_SECONDS,
    }
    return {
        "pairing_code": code,
        "expires_in_seconds": _PAIRING_TTL_SECONDS,
    }


@router.post("/devices/pair")
async def pair_device(
    data: PairRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Exchange a pairing code for a registered device + access token."""
    record = _pairing_codes.pop(data.pairing_code.strip(), None)
    if not record or record["expires_at"] < time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired pairing code")

    repo = DeviceRepository(db)
    token = f"dtk_{uuid.uuid4().hex}"
    device = await repo.create(
        name=data.device_name or data.hostname or "paired-device",
        hostname=data.hostname or "unknown",
        platform=data.platform,
        os_version=data.os_version,
    )
    caps = dict(device.capabilities or {})
    caps["device_token"] = token
    device.capabilities = caps
    await db.commit()
    await db.refresh(device)
    return {
        "device_id": device.id,
        "device_token": token,
        "agent_version": device.agent_version,
    }


@router.post("/devices/validate-token")
async def validate_device_token(
    data: TokenValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Validate a device token (used by the local agent on reconnect)."""
    repo = DeviceRepository(db)
    device = await repo.get_by_id(data.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    caps = device.capabilities or {}
    if caps.get("device_token") != data.device_token:
        raise HTTPException(status_code=401, detail="Invalid device token")
    return {"ok": True, "device_id": device.id, "valid": True}


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
