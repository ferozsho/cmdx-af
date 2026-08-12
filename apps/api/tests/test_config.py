"""Configuration persistence security tests."""

import json

from app.core import config


def test_runtime_settings_load_scrubs_disallowed_keys(
    tmp_path,
    monkeypatch,
) -> None:
    """Legacy secrets are removed from disk, not merely ignored in memory."""
    settings_file = tmp_path / "runtime_settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "DEEPSEEK_API_KEY": "legacy-secret",
                "MAX_AGENT_STEPS": "12",
            }
        )
    )
    monkeypatch.setattr(config, "_SETTINGS_FILE", settings_file)
    monkeypatch.setattr(config, "runtime_settings", {})

    config._load_runtime_settings()

    assert config.runtime_settings == {"MAX_AGENT_STEPS": "12"}
    assert json.loads(settings_file.read_text()) == {"MAX_AGENT_STEPS": "12"}
    assert settings_file.stat().st_mode & 0o777 == 0o600
