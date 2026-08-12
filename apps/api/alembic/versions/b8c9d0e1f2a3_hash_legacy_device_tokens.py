"""Hash legacy plaintext device tokens.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

import hashlib
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace legacy plaintext credentials with one-way SHA-256 hashes."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, capabilities FROM devices")
    ).mappings()
    update = sa.text(
        "UPDATE devices SET capabilities = :capabilities WHERE id = :device_id"
    ).bindparams(
        sa.bindparam("capabilities", type_=postgresql.JSONB),
    )
    for row in rows:
        capabilities = dict(row["capabilities"] or {})
        plaintext_token = capabilities.pop("device_token", None)
        if not plaintext_token:
            continue
        capabilities["device_token_hash"] = hashlib.sha256(
            str(plaintext_token).encode("utf-8")
        ).hexdigest()
        bind.execute(
            update,
            {
                "device_id": row["id"],
                "capabilities": capabilities,
            },
        )


def downgrade() -> None:
    """Do not recreate plaintext credentials during downgrade."""
