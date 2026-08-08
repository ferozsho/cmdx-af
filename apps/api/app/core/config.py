"""Application Configuration Settings."""

import json
import os
from pathlib import Path
from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


# Runtime-overridable settings (set by Settings page via API)
runtime_settings: Dict[str, str] = {}

# Persist runtime settings across restarts (JSON file on disk).
# config.py lives at <root>/app/core/config.py, so we need THREE parents to
# reach <root> (e.g. /app/apps/api) where the `data/` volume is mounted.
_SETTINGS_FILE = Path(
    os.environ.get(
        "AGENTFORGE_SETTINGS_FILE",
        str(
            Path(__file__).resolve().parent.parent.parent
            / "data"
            / "runtime_settings.json"
        ),
    )
)


def _load_runtime_settings() -> None:
    """Load persisted runtime settings from disk on startup."""
    try:
        if _SETTINGS_FILE.exists():
            runtime_settings.update(json.loads(_SETTINGS_FILE.read_text()))
    except Exception:
        pass


def save_runtime_settings() -> None:
    """Persist current runtime settings to disk."""
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(
            json.dumps(runtime_settings, indent=2, sort_keys=True)
        )
    except Exception:
        pass


def get_setting(key: str, default: str = "") -> str:
    """Get a setting value — runtime override takes precedence over env."""
    return runtime_settings.get(key) or default


_load_runtime_settings()


class Settings(BaseSettings):
    """Configuration settings for AgentForge Cloud Control Plane."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "AgentForge Cloud Control Plane"
    APP_ENV: str = "development"
    APP_MODE: str = "production"  # production or mock
    API_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "agentforge-super-secret-key-change-in-production-2026"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = (
        "postgresql+asyncpg://agentforge:agentforge123@localhost:5432/agentforge_db"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_CODER_MODEL: str = "deepseek-coder"

    RAG_TOP_K: int = 5
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50

    ENABLE_CONFIRMATION_BEFORE_DELETE: bool = True
    GIT_AUTHOR_NAME: str = "AgentForge AI"
    GIT_AUTHOR_EMAIL: str = "agent@agentforge.ai"


settings = Settings()
