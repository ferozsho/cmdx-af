"""Add session attribution to LLM usage records.

Revision ID: n0a1b2c3d4e5
Revises: m9a0b1c2d3e4
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n0a1b2c3d4e5"
down_revision: Union[str, None] = "m9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add llm_usage.session_id and backfill it from instruction sessions."""
    op.add_column(
        "llm_usage",
        sa.Column("session_id", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_llm_usage_session_id"), "llm_usage", ["session_id"]
    )
    op.create_foreign_key(
        "fk_llm_usage_session_id_sessions",
        "llm_usage",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Backfill: existing pipeline usage rows inherit their instruction's session.
    op.execute(
        """
        UPDATE llm_usage
        SET session_id = instructions.session_id
        FROM instructions
        WHERE llm_usage.instruction_id = instructions.id
          AND llm_usage.session_id IS NULL
          AND instructions.session_id IS NOT NULL
        """
    )


def downgrade() -> None:
    """Drop the session attribution column."""
    op.drop_constraint(
        "fk_llm_usage_session_id_sessions", "llm_usage", type_="foreignkey"
    )
    op.drop_index(op.f("ix_llm_usage_session_id"), table_name="llm_usage")
    op.drop_column("llm_usage", "session_id")
