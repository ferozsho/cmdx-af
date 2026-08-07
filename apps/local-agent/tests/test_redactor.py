"""Unit tests for Secret Redactor."""

from agentforge_local.security.secret_redactor import SecretRedactor


def test_secret_redactor_api_key() -> None:
    """Verify OpenAI/DeepSeek API keys are redacted."""
    raw = "My API key is sk-1234567890abcdef1234567890"
    redacted = SecretRedactor.redact(raw)
    assert "sk-1234567890abcdef1234567890" not in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_secret_redactor_bearer_token() -> None:
    """Verify Bearer tokens are redacted."""
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test"
    redacted = SecretRedactor.redact(raw)
    assert "Bearer [REDACTED_TOKEN]" in redacted
