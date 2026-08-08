"""add local_path column to projects

Revision ID: c7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-08-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add local_path to projects."""
    op.add_column(
        "projects",
        sa.Column("local_path", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drop local_path from projects."""
    op.drop_column("projects", "local_path")
