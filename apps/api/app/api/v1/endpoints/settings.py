"""Platform Settings API Endpoint."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_CHAT_MODEL,
    DEFAULT_RAG_CHUNK_OVERLAP,
    DEFAULT_RAG_CHUNK_SIZE,
    DEFAULT_RAG_TOP_K,
    get_setting,
    runtime_settings,
    save_runtime_settings,
)
from app.core.database import get_db
from app.core.secrets import REMOVE_KEY_SENTINEL
from app.core.security import get_current_admin, get_current_user
from app.llm.router import get_model_list
from app.services.platform_settings import remove_secret, set_secret

router = APIRouter()

# Map of provider -> environment/DB setting key that holds its API key.
PROVIDER_KEY_SETTINGS: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "CLAUDE_API_KEY",
}


class SettingsPayload(BaseModel):
    """Non-secret settings payload from the frontend."""

    # DeepSeek
    deepseek_base_url: str = ""
    deepseek_chat_model: str = ""

    # OpenAI
    openai_base_url: str = ""
    openai_chat_model: str = ""

    # Gemini
    gemini_chat_model: str = ""

    # Claude
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


class ApiKeyPayload(BaseModel):
    """Set, replace or remove a provider API key.

    ``api_key`` is the plaintext value to store. Pass ``"__remove__"`` to
    delete the key for the provider. Empty strings are rejected so a blank
    form submission never wipes an existing key.
    """

    provider: str
    api_key: str


@router.get("/settings")
async def get_settings(
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Return current non-secret platform settings. Admin only."""
    dsk = get_setting("DEEPSEEK_API_KEY", "")
    oak = get_setting("OPENAI_API_KEY", "")
    gak = get_setting("GEMINI_API_KEY", "")
    cak = get_setting("CLAUDE_API_KEY", "")

    return {
        # DeepSeek
        "deepseek_base_url": runtime_settings.get(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        ),
        "deepseek_chat_model": runtime_settings.get(
            "DEEPSEEK_CHAT_MODEL", DEFAULT_DEEPSEEK_CHAT_MODEL
        ),
        "has_deepseek_key": bool(dsk),
        # OpenAI
        "openai_base_url": runtime_settings.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        ),
        "openai_chat_model": runtime_settings.get(
            "OPENAI_CHAT_MODEL", "gpt-4o"
        ),
        "has_openai_key": bool(oak),
        # Gemini
        "gemini_chat_model": runtime_settings.get(
            "GEMINI_CHAT_MODEL", "gemini-2.5-pro"
        ),
        "has_gemini_key": bool(gak),
        # Claude
        "claude_chat_model": runtime_settings.get(
            "CLAUDE_CHAT_MODEL", "claude-3-5-sonnet-20241022"
        ),
        "has_claude_key": bool(cak),
        # General
        "max_agent_steps": int(runtime_settings.get("MAX_AGENT_STEPS", "10")),
        "agent_timeout": int(runtime_settings.get("AGENT_TIMEOUT", "600")),
        "rag_top_k": int(
            runtime_settings.get("RAG_TOP_K", str(DEFAULT_RAG_TOP_K))
        ),
        "rag_chunk_size": int(
            runtime_settings.get("RAG_CHUNK_SIZE", str(DEFAULT_RAG_CHUNK_SIZE))
        ),
        "rag_chunk_overlap": int(
            runtime_settings.get(
                "RAG_CHUNK_OVERLAP", str(DEFAULT_RAG_CHUNK_OVERLAP)
            )
        ),
        "rag_similarity_threshold": float(
            runtime_settings.get("RAG_SIMILARITY_THRESHOLD", "0.65")
        ),
        "context_window_budget": runtime_settings.get("CONTEXT_WINDOW_BUDGET", "30%"),
        "allowed_commands": runtime_settings.get(
            "ALLOWED_COMMANDS",
            "pip install, npm install, npm run build, python -m, npx, "
            "pytest, jest, ruff, eslint, mypy, bandit",
        ),
    }


@router.put("/settings")
async def update_settings(
    data: SettingsPayload,
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Update non-secret platform settings at runtime. Admin only."""
    # DeepSeek
    if data.deepseek_base_url:
        runtime_settings["DEEPSEEK_BASE_URL"] = data.deepseek_base_url
    if data.deepseek_chat_model:
        runtime_settings["DEEPSEEK_CHAT_MODEL"] = data.deepseek_chat_model

    # OpenAI
    if data.openai_base_url:
        runtime_settings["OPENAI_BASE_URL"] = data.openai_base_url
    if data.openai_chat_model:
        runtime_settings["OPENAI_CHAT_MODEL"] = data.openai_chat_model

    # Gemini
    if data.gemini_chat_model:
        runtime_settings["GEMINI_CHAT_MODEL"] = data.gemini_chat_model

    # Claude
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

    save_runtime_settings()
    return {
        "ok": True,
        "detail": "Settings saved. API keys are managed via /settings/keys.",
    }


@router.put("/settings/keys")
async def update_api_key(
    data: ApiKeyPayload,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_admin),
) -> Any:
    """Set, replace or remove a provider API key (encrypted at rest)."""
    key_setting = PROVIDER_KEY_SETTINGS.get(data.provider.strip().lower())
    if not key_setting:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider: {data.provider}",
        )

    api_key = data.api_key.strip()

    if api_key == REMOVE_KEY_SENTINEL:
        await remove_secret(db, key_setting)
        return {
            "ok": True,
            "detail": f"{data.provider} API key removed.",
        }

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key must not be empty (pass a value or __remove__).",
        )
    if len(api_key) < 8:
        raise HTTPException(
            status_code=400,
            detail="API key looks too short to be valid.",
        )

    await set_secret(db, key_setting, api_key)
    return {
        "ok": True,
        "detail": f"{data.provider} API key saved (encrypted at rest).",
    }


@router.get("/settings/models")
async def list_models(
    vision_only: bool = False,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Return models available to an authenticated user."""
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
            "key": get_setting("DEEPSEEK_API_KEY", ""),
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
            "key": get_setting("OPENAI_API_KEY", ""),
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
            "key": get_setting("GEMINI_API_KEY", ""),
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
            "key": get_setting("CLAUDE_API_KEY", ""),
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
