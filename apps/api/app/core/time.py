"""Consistent UTC timestamps for legacy timezone-naive database columns."""

from datetime import UTC, datetime


def naive_utcnow() -> datetime:
    """Return current UTC while preserving existing naive SQL column semantics."""
    return datetime.now(UTC).replace(tzinfo=None)
