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
from app.llm.router import get_model_list, MODEL_REGISTRY

router = APIRouter()


class SettingsPayload(BaseModel):
    """Settings payload from the frontend — multi-provider."""

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    deepseek_chat_model: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_chat_model: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_chat_model: str = ""

    # Claude
    claude_api_key: str = ""
    claude_chat_model: str = ""

    # General
    max_agent_steps: int = 10
    agent_timeout: int = 600
    rag_top_k: int = 5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_similarity_threshold: float = 0.65
    context_window_budget: str = "30%"
    allowed_commands: str = ""


def _mask_key(key: str) -> str:
    if not key:
        return ""
    return key[:4] + "••••" + key[-4:] if len(key) > 8 else "••••"


@router.get("/settings")
async def get_settings(
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Return current platform settings (masked API keys). Admin only."""
    dsk = runtime_settings.get("DEEPSEEK_API_KEY", "")
    oak = runtime_settings.get("OPENAI_API_KEY", "")
    gak = runtime_settings.get("GEMINI_API_KEY", "")
    cak = runtime_settings.get("CLAUDE_API_KEY", "")

    return {
        # DeepSeek
        "deepseek_api_key_masked": _mask_key(dsk),
        "deepseek_base_url": runtime_settings.get(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        ),
        "deepseek_chat_model": runtime_settings.get(
            "DEEPSEEK_CHAT_MODEL", DEFAULT_DEEPSEEK_CHAT_MODEL
        ),
        "has_deepseek_key": bool(dsk),
        # OpenAI
        "openai_api_key_masked": _mask_key(oak),
        "openai_base_url": runtime_settings.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        ),
        "openai_chat_model": runtime_settings.get(
            "OPENAI_CHAT_MODEL", "gpt-4o"
        ),
        "has_openai_key": bool(oak),
        # Gemini
        "gemini_api_key_masked": _mask_key(gak),
        "gemini_chat_model": runtime_settings.get(
            "GEMINI_CHAT_MODEL", "gemini-2.5-pro"
        ),
        "has_gemini_key": bool(gak),
        # Claude
        "claude_api_key_masked": _mask_key(cak),
        "claude_chat_model": runtime_settings.get(
            "CLAUDE_CHAT_MODEL", "claude-3-5-sonnet-20241022"
        ),
        "has_claude_key": bool(cak),
        # General
        "max_agent_steps": int(runtime_settings.get("MAX_AGENT_STEPS", "10")),
        "agent_timeout": int(runtime_settings.get("AGENT_TIMEOUT", "600")),
        "rag_top_k": int(runtime_settings.get("RAG_TOP_K", str(DEFAULT_RAG_TOP_K))),
        "rag_chunk_size": int(runtime_settings.get("RAG_CHUNK_SIZE", str(DEFAULT_RAG_CHUNK_SIZE))),
        "rag_chunk_overlap": int(runtime_settings.get("RAG_CHUNK_OVERLAP", str(DEFAULT_RAG_CHUNK_OVERLAP))),
        "rag_similarity_threshold": float(runtime_settings.get("RAG_SIMILARITY_THRESHOLD", "0.65")),
        "context_window_budget": runtime_settings.get("CONTEXT_WINDOW_BUDGET", "30%"),
        "allowed_commands": runtime_settings.get(
            "ALLOWED_COMMANDS",
            "pip install, npm install, npm run build, python -m, npx, pytest, jest, ruff, eslint, mypy, bandit",
        ),
    }


@router.put("/settings")
async def update_settings(
    data: SettingsPayload,
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Update platform settings at runtime. Admin only."""
    # DeepSeek
    if data.deepseek_api_key:
        runtime_settings["DEEPSEEK_API_KEY"] = data.deepseek_api_key
    if data.deepseek_base_url:
        runtime_settings["DEEPSEEK_BASE_URL"] = data.deepseek_base_url
    if data.deepseek_chat_model:
        runtime_settings["DEEPSEEK_CHAT_MODEL"] = data.deepseek_chat_model

    # OpenAI
    if data.openai_api_key:
        runtime_settings["OPENAI_API_KEY"] = data.openai_api_key
    if data.openai_base_url:
        runtime_settings["OPENAI_BASE_URL"] = data.openai_base_url
    if data.openai_chat_model:
        runtime_settings["OPENAI_CHAT_MODEL"] = data.openai_chat_model

    # Gemini
    if data.gemini_api_key:
        runtime_settings["GEMINI_API_KEY"] = data.gemini_api_key
    if data.gemini_chat_model:
        runtime_settings["GEMINI_CHAT_MODEL"] = data.gemini_chat_model

    # Claude
    if data.claude_api_key:
        runtime_settings["CLAUDE_API_KEY"] = data.claude_api_key
    if data.claude_chat_model:
        runtime_settings["CLAUDE_CHAT_MODEL"] = data.claude_chat_model

    # General
    runtime_settings["MAX_AGENT_STEPS"] = str(data.max_agent_steps)
    runtime_settings["AGENT_TIMEOUT"] = str(data.agent_timeout)
    runtime_settings["RAG_TOP_K"] = str(data.rag_top_k)
    runtime_settings["RAG_CHUNK_SIZE"] = str(data.rag_chunk_size)
    runtime_settings["RAG_CHUNK_OVERLAP"] = str(data.rag_chunk_overlap)
    runtime_settings["RAG_SIMILARITY_THRESHOLD"] = str(data.rag_similarity_threshold)
    runtime_settings["CONTEXT_WINDOW_BUDGET"] = data.context_window_budget
    runtime_settings["ALLOWED_COMMANDS"] = data.allowed_commands

    has_any_key = bool(
        runtime_settings.get("DEEPSEEK_API_KEY")
        or runtime_settings.get("OPENAI_API_KEY")
        or runtime_settings.get("GEMINI_API_KEY")
        or runtime_settings.get("CLAUDE_API_KEY")
    )
    if has_any_key:
        settings.APP_MODE = "production"

    save_runtime_settings()
    return {"ok": True, "detail": "Settings updated"}


@router.get("/settings/models")
async def list_models(
    vision_only: bool = False,
) -> Any:
    """Return all registered LLM models with their capabilities."""
    models = get_model_list()
    if vision_only:
        models = [m for m in models if m["vision"]]
    return models


@router.post("/settings/test-connection/{provider}")
async def test_provider_connection(
    provider: str,
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Test connection to a specific LLM provider using its configured key."""
    import httpx

    providers: dict[str, dict] = {
        "deepseek": {
            "key": runtime_settings.get("DEEPSEEK_API_KEY", ""),
            "url": runtime_settings.get(
                "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
            )
            + "/chat/completions",
            "model": runtime_settings.get(
                "DEEPSEEK_CHAT_MODEL", DEFAULT_DEEPSEEK_CHAT_MODEL
            ),
            "headers": lambda k: {
                "Authorization": f"Bearer {k}",
                "Content-Type": "application/json",
            },
            "body": lambda m: {
                "model": m,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            },
        },
        "openai": {
            "key": runtime_settings.get("OPENAI_API_KEY", ""),
            "url": runtime_settings.get(
                "OPENAI_BASE_URL", "https://api.openai.com/v1"
            )
            + "/chat/completions",
            "model": runtime_settings.get("OPENAI_CHAT_MODEL", "gpt-4o"),
            "headers": lambda k: {
                "Authorization": f"Bearer {k}",
                "Content-Type": "application/json",
            },
            "body": lambda m: {
                "model": m,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            },
        },
        "gemini": {
            "key": runtime_settings.get("GEMINI_API_KEY", ""),
            "url": lambda m: (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{m}:generateContent"
            ),
            "model": runtime_settings.get(
                "GEMINI_CHAT_MODEL", "gemini-2.5-pro"
            ),
            "headers": lambda k: {"x-goog-api-key": k},
            "body": lambda m: {
                "contents": [{"parts": [{"text": "Hi"}]}],
            },
        },
        "claude": {
            "key": runtime_settings.get("CLAUDE_API_KEY", ""),
            "url": "https://api.anthropic.com/v1/messages",
            "model": runtime_settings.get(
                "CLAUDE_CHAT_MODEL", "claude-3-5-sonnet-20241022"
            ),
            "headers": lambda k: {
                "x-api-key": k,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            "body": lambda m: {
                "model": m,
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "Hi"}],
            },
        },
    }

    cfg = providers.get(provider)
    if not cfg:
        return {"ok": False, "error": f"Unknown provider: {provider}"}

    api_key = cfg["key"]
    if not api_key:
        return {"ok": False, "error": f"No API key configured for {provider}"}

    model = cfg["model"]
    headers = cfg["headers"](api_key) if callable(cfg["headers"]) else cfg["headers"]
    body = cfg["body"](model) if callable(cfg["body"]) else cfg["body"]
    url = cfg["url"](model) if callable(cfg["url"]) else cfg["url"]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=body)
            if res.status_code in (200, 201):
                return {"ok": True, "detail": f"Connected to {provider} ({model})"}
            err_detail = ""
            try:
                err_detail = res.json()
            except Exception:
                err_detail = res.text[:200]
            return {
                "ok": False,
                "error": f"HTTP {res.status_code}: {err_detail}",
            }
    except httpx.TimeoutException:
        return {"ok": False, "error": f"Connection to {provider} timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
