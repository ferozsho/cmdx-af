"""Add durable one-time credentials and image media type.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist pairing/reset credentials and attachment media types."""
    op.add_column(
        "instructions",
        sa.Column("image_mime_type", sa.String(), nullable=True),
    )
    for table_name, hash_column in (
        ("pairing_codes", "code_hash"),
        ("password_reset_tokens", "token_hash"),
    ):
        op.create_table(
            table_name,
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column(hash_column, sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(hash_column),
        )
        op.create_index(
            f"ix_{table_name}_user_id",
            table_name,
            ["user_id"],
        )


def downgrade() -> None:
    """Remove durable one-time credential storage."""
    for table_name in ("password_reset_tokens", "pairing_codes"):
        op.drop_index(f"ix_{table_name}_user_id", table_name=table_name)
        op.drop_table(table_name)
    op.drop_column("instructions", "image_mime_type")
