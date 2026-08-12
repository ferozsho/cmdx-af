"""Local Agent Daemon Configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class LocalAgentSettings(BaseSettings):
    """Local Agent configuration options."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    CLOUD_WSS_URL: str = "ws://localhost:8000/api/v1/ws/devices"
    CLOUD_API_URL: str = "http://localhost:8000/api/v1"
    CONFIG_DIR: Path = Path.home() / ".agentforge"
    DEVICE_ID: str | None = None
    DEVICE_TOKEN: str | None = None
    # Optional human-readable device name (shown on the Devices page). Falls
    # back to the machine hostname when unset.
    AGENTFORGE_DEVICE_NAME: str | None = None
    HEARTBEAT_INTERVAL: int = 15

    # Qdrant vector store (local or docker-published endpoint)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None


local_settings = LocalAgentSettings()
