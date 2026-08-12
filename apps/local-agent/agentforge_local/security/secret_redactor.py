"""Secret Redaction Module for Preventing Credential Leaks."""

import re

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (
        re.compile(r"bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*", re.IGNORECASE),
        "Bearer [REDACTED_TOKEN]",
    ),
    (
        re.compile(
            r"(postgres|mysql|mongodb|redis):\/\/[^\s]+:[^\s]+@",
            re.IGNORECASE,
        ),
        r"\1://[REDACTED_DB_CREDS]@",
    ),
    (
        re.compile(
            r"(password|passwd|secret|api_key)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
            re.IGNORECASE,
        ),
        r"\1: [REDACTED_SECRET]",
    ),
    (
        re.compile(
            r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----[\s\S]+?"
            r"-----END \1 PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


class SecretRedactor:
    """Utility for sanitizing output text to prevent accidental credential leakage."""

    @classmethod
    def redact(cls, text: str) -> str:
        """Sanitize text by replacing matched sensitive patterns."""
        if not text:
            return text

        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized
