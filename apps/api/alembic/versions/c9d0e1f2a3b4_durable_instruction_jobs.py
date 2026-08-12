"""Add durable instruction jobs and replayable events.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add queue state to instructions and a durable event journal."""
    op.add_column(
        "instructions",
        sa.Column("idempotency_key", sa.String(), nullable=True),
    )
    op.add_column(
        "instructions",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "instructions",
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )
    op.add_column(
        "instructions",
        sa.Column(
            "available_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "instructions",
        sa.Column("started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "instructions",
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "instructions",
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "instructions",
        sa.Column("cancel_requested_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "instructions",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_instructions_project_idempotency_key",
        "instructions",
        ["project_id", "idempotency_key"],
    )
    op.create_index(
        "ix_instructions_queue",
        "instructions",
        ["status", "available_at", "created_at"],
    )
    op.create_table(
        "instruction_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("instruction_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instruction_id"],
            ["instructions.id"],
            name="instruction_events_instruction_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="instruction_events_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_instruction_events_project_id",
        "instruction_events",
        ["project_id"],
    )
    op.create_index(
        "ix_instruction_events_instruction_id",
        "instruction_events",
        ["instruction_id"],
    )


def downgrade() -> None:
    """Remove the durable job queue and event journal."""
    op.drop_index(
        "ix_instruction_events_instruction_id",
        table_name="instruction_events",
    )
    op.drop_index(
        "ix_instruction_events_project_id",
        table_name="instruction_events",
    )
    op.drop_table("instruction_events")
    op.drop_index("ix_instructions_queue", table_name="instructions")
    op.drop_constraint(
        "uq_instructions_project_idempotency_key",
        "instructions",
        type_="unique",
    )
    for column in (
        "last_error",
        "cancel_requested_at",
        "finished_at",
        "heartbeat_at",
        "started_at",
        "available_at",
        "max_attempts",
        "attempt_count",
        "idempotency_key",
    ):
        op.drop_column("instructions", column)
