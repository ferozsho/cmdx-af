"""Add durable verification evidence.

Revision ID: j6e7f8g9h0i1
Revises: i5d6e7f8g9h0
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "j6e7f8g9h0i1"
down_revision: Union[str, None] = "i5d6e7f8g9h0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("instruction_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("executable", sa.String(), nullable=False),
        sa.Column("command_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("output_digest", sa.String(64), nullable=False),
        sa.Column("output_excerpt", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["instruction_id"], ["instructions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "instruction_id", "category", "status"):
        op.create_index(
            f"ix_verification_runs_{column}", "verification_runs", [column]
        )


def downgrade() -> None:
    for column in ("status", "category", "instruction_id", "project_id"):
        op.drop_index(
            f"ix_verification_runs_{column}", table_name="verification_runs"
        )
    op.drop_table("verification_runs")
