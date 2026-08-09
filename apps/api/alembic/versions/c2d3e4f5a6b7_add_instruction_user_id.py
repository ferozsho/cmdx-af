"""add user_id to instructions for query history tracking

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "instructions",
        sa.Column("user_id", sa.String(), nullable=True),
    )
    # Create index for user-scoped queries
    op.create_index("ix_instructions_user_id", "instructions", ["user_id"])
    op.create_index(
        "ix_instructions_project_user",
        "instructions",
        ["project_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_instructions_project_user")
    op.drop_index("ix_instructions_user_id")
    op.drop_column("instructions", "user_id")
