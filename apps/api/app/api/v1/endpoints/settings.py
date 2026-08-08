"""Platform Settings API Endpoint."""

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.config import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_CHAT_MODEL,
    DEFAULT_DEEPSEEK_CODER_MODEL,
    DEFAULT_RAG_CHUNK_OVERLAP,
    DEFAULT_RAG_CHUNK_SIZE,
    DEFAULT_RAG_TOP_K,
    runtime_settings,
    save_runtime_settings,
    settings,
)
from app.core.security import get_current_admin

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
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_similarity_threshold: float = 0.65
    context_window_budget: str = "30%"
    allowed_commands: str = ""


@router.get("/settings")
async def get_settings(
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Return current platform settings (masked API key). Admin only."""
    api_key = runtime_settings.get("DEEPSEEK_API_KEY", "")
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
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        ),
        "chat_model": runtime_settings.get(
            "DEEPSEEK_CHAT_MODEL", DEFAULT_DEEPSEEK_CHAT_MODEL
        ),
        "coder_model": runtime_settings.get(
            "DEEPSEEK_CODER_MODEL", DEFAULT_DEEPSEEK_CODER_MODEL
        ),
        "max_agent_steps": int(
            runtime_settings.get("MAX_AGENT_STEPS", "10")
        ),
        "agent_timeout": int(
            runtime_settings.get("AGENT_TIMEOUT", "600")
        ),
        "rag_top_k": int(
            runtime_settings.get("RAG_TOP_K", DEFAULT_RAG_TOP_K)
        ),
        "rag_chunk_size": int(
            runtime_settings.get("RAG_CHUNK_SIZE", DEFAULT_RAG_CHUNK_SIZE)
        ),
        "rag_chunk_overlap": int(
            runtime_settings.get(
                "RAG_CHUNK_OVERLAP", DEFAULT_RAG_CHUNK_OVERLAP
            )
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
async def update_settings(
    data: SettingsPayload,
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Update platform settings at runtime. Admin only."""
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
    runtime_settings["RAG_CHUNK_SIZE"] = str(data.rag_chunk_size)
    runtime_settings["RAG_CHUNK_OVERLAP"] = str(data.rag_chunk_overlap)
    runtime_settings["RAG_SIMILARITY_THRESHOLD"] = str(
        data.rag_similarity_threshold
    )
    runtime_settings["CONTEXT_WINDOW_BUDGET"] = data.context_window_budget
    runtime_settings["ALLOWED_COMMANDS"] = data.allowed_commands

    if runtime_settings.get("DEEPSEEK_API_KEY"):
        settings.APP_MODE = "production"

    # Persist across restarts
    save_runtime_settings()

    return {"ok": True, "detail": "Settings updated"}
