"""Device pairing and credential storage for the Local Agent."""

import json
import platform as platform_mod
import socket
from pathlib import Path
from typing import Any, Dict

from agentforge_local.config import local_settings


def _device_config_path() -> Path:
    """Path to the persisted device credentials file."""
    return local_settings.CONFIG_DIR / "device.json"


def load_device_credentials() -> Dict[str, str]:
    """Load {device_id, device_token} from disk, if present."""
    path = _device_config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
    return {}


def save_device_identity(device_id: str) -> None:
    """Persist only the non-secret paired device identity to disk."""
    creds = load_device_credentials()
    creds.pop("device_token", None)
    creds["device_id"] = device_id
    path = _device_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(creds, indent=2))
    path.chmod(0o600)


def system_info() -> Dict[str, Any]:
    """Collect basic workstation metadata for pairing."""
    return {
        "device_name": platform_mod.node() or "workstation",
        "hostname": socket.gethostname() or "unknown",
        "platform": platform_mod.system().lower() or "unknown",
        "os_version": platform_mod.version() or None,
    }


async def pair_with_cloud(pairing_code: str) -> Dict[str, Any]:
    """Exchange a pairing code for device credentials via the cloud API."""
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        info = system_info()
        res = await client.post(
            f"{local_settings.CLOUD_API_URL}/devices/pair",
            json={"pairing_code": pairing_code, **info},
        )
        res.raise_for_status()
        data = res.json()
        save_device_identity(data["device_id"])
        return data
