"""create sessions table and add session_id to instructions

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-09
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False, server_default="New Session"),
        sa.Column("model_name", sa.String(), nullable=False, server_default="deepseek-chat"),
        sa.Column("context_limit", sa.Integer(), nullable=False, server_default="65536"),
        sa.Column("total_tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_sessions_project_id", "sessions", ["project_id"])

    # Add session_id to instructions
    op.add_column(
        "instructions",
        sa.Column("session_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_instructions_session_id",
        "instructions",
        "sessions",
        ["session_id"],
        ["id"],
    )
    op.create_index(
        "ix_instructions_session_id",
        "instructions",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_instructions_session_id")
    op.drop_constraint("fk_instructions_session_id", "instructions", type_="foreignkey")
    op.drop_column("instructions", "session_id")
    op.drop_index("ix_sessions_project_id")
    op.drop_table("sessions")
