"""Application Configuration Settings."""

import json
import logging
from pathlib import Path
from typing import Dict
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_REPO_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"

SECRET_SETTING_KEYS = frozenset(
    {
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "CLAUDE_API_KEY",
        "QDRANT_API_KEY",
    }
)

RUNTIME_SETTING_KEYS = frozenset(
    {
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_CHAT_MODEL",
        "DEEPSEEK_MAX_TOKENS",
        "OPENAI_BASE_URL",
        "OPENAI_CHAT_MODEL",
        "OPENAI_MAX_TOKENS",
        "GEMINI_CHAT_MODEL",
        "CLAUDE_CHAT_MODEL",
        "MAX_AGENT_STEPS",
        "AGENT_TIMEOUT",
        "RAG_TOP_K",
        "RAG_CHUNK_SIZE",
        "RAG_CHUNK_OVERLAP",
        "RAG_SIMILARITY_THRESHOLD",
        "CONTEXT_WINDOW_BUDGET",
        "ALLOWED_COMMANDS",
    }
)


# Non-secret runtime-overridable settings (set by Settings page via API).
runtime_settings: Dict[str, str] = {}

# DB-backed secrets (LLM API keys) cached in memory. Populated at startup from
# the `platform_settings` table and refreshed after key updates via the API.
# Kept in-process so the synchronous `get_setting()` used by the LLM layer,
# worker and health checks works without a DB session at call time.
db_secret_settings: Dict[str, str] = {}

# Persist runtime settings across restarts (JSON file on disk).
# config.py lives at <root>/app/core/config.py, so we need THREE parents to
# reach <root> (e.g. /app/apps/api) where the `data/` volume is mounted.
_SETTINGS_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "runtime_settings.json"
)


def _load_runtime_settings() -> None:
    """Load only allowlisted, non-secret runtime settings from disk."""
    try:
        if _SETTINGS_FILE.exists():
            raw = json.loads(_SETTINGS_FILE.read_text())
            if not isinstance(raw, dict):
                raise ValueError("runtime settings must be a JSON object")
            runtime_settings.update(
                {
                    key: str(value)
                    for key, value in raw.items()
                    if key in RUNTIME_SETTING_KEYS
                }
            )
            ignored = set(raw) - RUNTIME_SETTING_KEYS
            if ignored:
                logger.warning(
                    "Removed disallowed runtime setting keys: %s",
                    ", ".join(sorted(ignored)),
                )
                save_runtime_settings()
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        logger.exception("Unable to load runtime settings")


def save_runtime_settings() -> None:
    """Atomically persist only allowlisted, non-secret runtime settings."""
    temporary_file = _SETTINGS_FILE.with_suffix(
        f"{_SETTINGS_FILE.suffix}.{uuid4().hex}.tmp"
    )
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        safe_settings = {
            key: value
            for key, value in runtime_settings.items()
            if key in RUNTIME_SETTING_KEYS
        }
        temporary_file.write_text(
            json.dumps(safe_settings, indent=2, sort_keys=True)
        )
        temporary_file.chmod(0o600)
        temporary_file.replace(_SETTINGS_FILE)
    except OSError:
        logger.exception("Unable to persist runtime settings")
        temporary_file.unlink(missing_ok=True)


def get_setting(key: str, default: str = "") -> str:
    """Resolve a setting without permitting runtime overrides for secrets.

    API keys are managed EXCLUSIVELY from the Settings page (DB-backed
    ``platform_settings`` table). They are never read from .env, so a key
    only takes effect once it is stored in Settings.
    """
    if key in SECRET_SETTING_KEYS:
        # Secrets come ONLY from the DB-backed settings store. No .env
        # fallback — the Settings page is the single source of truth.
        return db_secret_settings.get(key) or default
    runtime_value = runtime_settings.get(key)
    if runtime_value:
        return runtime_value
    configured = getattr(settings, key, None)
    return str(configured) if configured not in (None, "") else default


# Non-secret model and provider defaults may be changed from the Settings page.
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_CHAT_MODEL = "deepseek-chat"
DEFAULT_DEEPSEEK_CODER_MODEL = "deepseek-coder"
# DeepSeek's max output for deepseek-chat is 8192 tokens; a generous default
# prevents long structured outputs (e.g. file content in JSON) from being
# truncated mid-object, which otherwise yields invalid JSON.
DEFAULT_DEEPSEEK_MAX_TOKENS = "8192"
DEFAULT_OPENAI_MAX_TOKENS = "16384"

# Non-secret RAG defaults may be changed from the Settings page.
DEFAULT_RAG_TOP_K = "5"
DEFAULT_RAG_CHUNK_SIZE = "500"
DEFAULT_RAG_CHUNK_OVERLAP = "50"


_load_runtime_settings()


class Settings(BaseSettings):
    """Configuration settings for AgentForge Cloud Control Plane."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AgentForge Cloud Control Plane"
    APP_ENV: str = "development"
    APP_MODE: str = "production"  # production or mock
    API_PREFIX: str = "/api/v1"

    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = Field(min_length=1)
    REDIS_URL: str = Field(min_length=1)

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None

    DEEPSEEK_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""

    # Max output tokens for structured/completion calls. Kept high so large
    # JSON payloads (complete file content) are not silently truncated.
    DEEPSEEK_MAX_TOKENS: str = "8192"
    OPENAI_MAX_TOKENS: str = "16384"

    CORS_ORIGINS: str = "http://localhost:3000"

    # Service-to-service auth: shared secret the worker uses to relay tool
    # calls through the API (which holds the live device WebSocket sessions).
    INTERNAL_API_TOKEN: str = ""
    # Base URL of the API used by the worker's tool-gateway relay. Empty in
    # the API process (uses its local WSS manager); set in the worker compose
    # service (e.g. http://api:8000).
    TOOL_GATEWAY_URL: str = ""

    ENABLE_CONFIRMATION_BEFORE_DELETE: bool = True
    GIT_AUTHOR_NAME: str = "AgentForge AI"
    GIT_AUTHOR_EMAIL: str = "agent@agentforge.ai"

    # API-wide rate limiting (G1): ceilings per user and per client IP for
    # mutating/tool endpoints; auth endpoints keep their own tighter limits.
    RATE_LIMIT_MUTATING_PER_MIN: int = 30
    RATE_LIMIT_IP_PER_MIN: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def cors_origins(self) -> list[str]:
        """Return the configured explicit CORS origin allowlist."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
