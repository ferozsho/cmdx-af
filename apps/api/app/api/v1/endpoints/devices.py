"""Devices and Workstation Pairing Endpoints."""

import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    hash_device_token,
    verify_device_token,
)
from app.models.pairing_code import PairingCode
from app.models.user import User
from app.repositories.device_repo import DeviceRepository

router = APIRouter()

_PAIRING_TTL_SECONDS = 600
_PAIRING_ALPHABET = string.ascii_uppercase + string.digits


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
async def list_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get all registered workstation devices for the authenticated user."""
    repo = DeviceRepository(db)
    devices = await repo.list_for_user(current_user.id)
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
async def generate_pairing_code(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Generate and durably store a one-time local-agent pairing code."""
    code = "".join(secrets.choice(_PAIRING_ALPHABET) for _ in range(8))
    db.add(
        PairingCode(
            user_id=current_user.id,
            code_hash=hash_device_token(code),
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            + timedelta(seconds=_PAIRING_TTL_SECONDS),
        )
    )
    await db.commit()
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
    now = datetime.now(UTC).replace(tzinfo=None)
    result = await db.execute(
        select(PairingCode)
        .where(
            PairingCode.code_hash
            == hash_device_token(data.pairing_code.strip()),
            PairingCode.used_at.is_(None),
            PairingCode.expires_at >= now,
        )
        .with_for_update()
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired pairing code")
    record.used_at = now

    repo = DeviceRepository(db)
    token = f"dtk_{uuid.uuid4().hex}"
    device = await repo.create(
        name=data.device_name or data.hostname or "paired-device",
        hostname=data.hostname or "unknown",
        platform=data.platform,
        user_id=record.user_id,
        os_version=data.os_version,
    )
    caps = dict(device.capabilities or {})
    caps["device_token_hash"] = hash_device_token(token)
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
    if not verify_device_token(
        data.device_token,
        str(caps.get("device_token_hash") or ""),
    ):
        raise HTTPException(status_code=401, detail="Invalid device token")
    return {"ok": True, "device_id": device.id, "valid": True}


@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Revoke a registered device: disconnect WSS and remove from DB."""
    from app.wss.connection_manager import wss_manager

    repo = DeviceRepository(db)
    device = await repo.get_by_id(device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")
    if wss_manager.is_device_online(device_id):
        await wss_manager.disconnect(device_id, db)
    deleted = await repo.delete(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True, "detail": f"Device {device_id} revoked"}
