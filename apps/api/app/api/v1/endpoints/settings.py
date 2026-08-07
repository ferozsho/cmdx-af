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
    max_agent_steps: int = 10
    agent_timeout: int = 600
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.65
    context_window_budget: str = "30%"
    allowed_commands: str = ""


@router.get("/settings")
async def get_settings() -> Any:
    """Return current platform settings (masked API key)."""
    api_key = runtime_settings.get(
        "DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY
    )
    masked = ""
    if api_key:
        masked = (
            api_key[:4] + "••••" + api_key[-4:]
            if len(api_key) > 8
            else "••••"
        )
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
        "max_agent_steps": int(
            runtime_settings.get("MAX_AGENT_STEPS", "10")
        ),
        "agent_timeout": int(
            runtime_settings.get("AGENT_TIMEOUT", "600")
        ),
        "rag_top_k": int(
            runtime_settings.get("RAG_TOP_K", "5")
        ),
        "rag_similarity_threshold": float(
            runtime_settings.get("RAG_SIMILARITY_THRESHOLD", "0.65")
        ),
        "context_window_budget": runtime_settings.get(
            "CONTEXT_WINDOW_BUDGET", "30%"
        ),
        "allowed_commands": runtime_settings.get(
            "ALLOWED_COMMANDS",
            "pip install, npm install, npm run build, python -m, npx, pytest, jest, ruff, eslint, mypy, bandit",
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
    runtime_settings["MAX_AGENT_STEPS"] = str(data.max_agent_steps)
    runtime_settings["AGENT_TIMEOUT"] = str(data.agent_timeout)
    runtime_settings["RAG_TOP_K"] = str(data.rag_top_k)
    runtime_settings["RAG_SIMILARITY_THRESHOLD"] = str(
        data.rag_similarity_threshold
    )
    runtime_settings["CONTEXT_WINDOW_BUDGET"] = data.context_window_budget
    runtime_settings["ALLOWED_COMMANDS"] = data.allowed_commands

    if runtime_settings.get("DEEPSEEK_API_KEY") or settings.DEEPSEEK_API_KEY:
        settings.APP_MODE = "production"

    return {"ok": True, "detail": "Settings updated"}
