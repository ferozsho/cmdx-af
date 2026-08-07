"""Local Agent Daemon Configuration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalAgentSettings(BaseSettings):
    """Local Agent configuration options."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    CLOUD_WSS_URL: str = "ws://localhost:8000/api/v1/ws/devices"
    CLOUD_API_URL: str = "http://localhost:8000/api/v1"
    CONFIG_DIR: Path = Path.home() / ".agentforge"
    DEVICE_ID: str | None = None
    DEVICE_TOKEN: str | None = None
    HEARTBEAT_INTERVAL: int = 15


local_settings = LocalAgentSettings()
