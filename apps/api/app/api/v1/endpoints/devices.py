"""Devices and Workstation Pairing Endpoints."""

import uuid
from typing import Any, List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DeviceResponse(BaseModel):
    """Registered device response schema."""

    id: str
    name: str
    hostname: str
    platform: str
    status: str
    agent_version: str = "0.1.0"


MOCK_DEVICES = [
    {
        "id": "dev_feroz_pc",
        "name": "FEROZ-PC",
        "hostname": "FEROZ-PC",
        "platform": "Windows 11 Pro",
        "status": "online",
        "agent_version": "0.1.0",
    }
]


@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices() -> Any:
    """Get all registered workstation devices."""
    return MOCK_DEVICES


@router.post("/devices/pairing-code")
async def generate_pairing_code() -> Any:
    """Generate temporary 8-character pairing code for Local Agent onboarding."""
    return {
        "pairing_code": f"AGF-{uuid.uuid4().hex[:4].upper()}",
        "expires_in_seconds": 600,
    }
