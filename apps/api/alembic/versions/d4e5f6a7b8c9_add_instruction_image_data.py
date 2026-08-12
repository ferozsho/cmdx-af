"""add image_data to instructions for visual analysis attachments

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-08-09
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "instructions",
        sa.Column("image_data", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("instructions", "image_data")
