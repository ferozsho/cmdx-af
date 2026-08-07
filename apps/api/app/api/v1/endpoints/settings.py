"""Platform Settings API Endpoint."""

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import runtime_settings, settings

router = APIRouter()


class SettingsPayload(BaseModel):
    """Settings payload from the frontend."""

    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    chat_model: str = ""
    coder_model: str = ""


@router.get("/settings")
async def get_settings() -> Any:
    """Return current platform settings (masked API key)."""
    api_key = runtime_settings.get(
        "DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY
    )
    masked = ""
    if api_key:
        masked = api_key[:4] + "••••" + api_key[-4:] if len(api_key) > 8 else "••••"
    return {
        "deepseek_api_key_masked": masked,
        "deepseek_base_url": runtime_settings.get(
            "DEEPSEEK_BASE_URL", settings.DEEPSEEK_BASE_URL
        ),
        "chat_model": runtime_settings.get(
            "DEEPSEEK_CHAT_MODEL", settings.DEEPSEEK_CHAT_MODEL
        ),
        "coder_model": runtime_settings.get(
            "DEEPSEEK_CODER_MODEL", settings.DEEPSEEK_CODER_MODEL
        ),
        "has_key": bool(api_key),
    }


@router.put("/settings")
async def update_settings(data: SettingsPayload) -> Any:
    """Update platform settings at runtime."""
    if data.deepseek_api_key:
        runtime_settings["DEEPSEEK_API_KEY"] = data.deepseek_api_key
    if data.deepseek_base_url:
        runtime_settings["DEEPSEEK_BASE_URL"] = data.deepseek_base_url
    if data.chat_model:
        runtime_settings["DEEPSEEK_CHAT_MODEL"] = data.chat_model
    if data.coder_model:
        runtime_settings["DEEPSEEK_CODER_MODEL"] = data.coder_model

    # Switch to production mode if a real API key is set
    if runtime_settings.get("DEEPSEEK_API_KEY"):
        settings.APP_MODE = "production"

    return {"ok": True, "detail": "Settings updated"}
