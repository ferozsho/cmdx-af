"""Add DB-backed platform settings (encrypted secrets).

Revision ID: m9a0b1c2d3e4
Revises: l8g9h0i1j2k3
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m9a0b1c2d3e4"
down_revision: Union[str, None] = "l8g9h0i1j2k3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the platform_settings table."""
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    """Drop the platform_settings table."""
    op.drop_table("platform_settings")
