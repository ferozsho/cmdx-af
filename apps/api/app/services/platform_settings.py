"""DB-backed platform settings service.

Secrets (LLM API keys) are stored encrypted in the ``platform_settings`` table
and cached in-process (``app.core.config.db_secret_settings``) so that the
synchronous ``get_setting()`` used across the LLM layer, worker and health
checks can resolve them without a DB session at every call site.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import db_secret_settings
from app.core.database import AsyncSessionLocal
from app.core.secrets import decrypt_secret, encrypt_secret
from app.repositories.platform_setting_repo import PlatformSettingRepository

logger = logging.getLogger(__name__)


async def load_db_secrets() -> None:
    """Load all DB-stored secrets into the in-memory cache (startup hook)."""
    try:
        async with AsyncSessionLocal() as db:
            repo = PlatformSettingRepository(db)
            rows = await repo.list_secrets()
        loaded: dict[str, str] = {}
        for row in rows:
            if not row.value:
                continue
            plaintext = decrypt_secret(row.value)
            if plaintext:
                loaded[row.key] = plaintext
            else:
                logger.warning(
                    "Unable to decrypt stored secret %s; ignoring it", row.key
                )
        db_secret_settings.clear()
        db_secret_settings.update(loaded)
        if loaded:
            logger.info(
                "Loaded %d DB-backed secret(s): %s",
                len(loaded),
                ", ".join(sorted(loaded)),
            )
    except Exception:
        # Never block API startup on a failed secret load; .env fallback
        # still applies via get_setting().
        logger.exception("Failed to load DB-backed secrets at startup")


async def set_secret(db: AsyncSession, key: str, plaintext: str) -> None:
    """Encrypt and persist a secret, then refresh the in-memory cache."""
    repo = PlatformSettingRepository(db)
    await repo.upsert(key, encrypt_secret(plaintext), is_secret=True)
    await db.commit()
    db_secret_settings[key] = plaintext


async def remove_secret(db: AsyncSession, key: str) -> bool:
    """Delete a secret row and drop it from the in-memory cache."""
    repo = PlatformSettingRepository(db)
    removed = await repo.delete(key)
    await db.commit()
    db_secret_settings.pop(key, None)
    return removed
