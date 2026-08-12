"""Add approval workflows and command policy.

Revision ID: g3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "g3b4c5d6e7f8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_COMMANDS = (
    '["pytest", "npm", "pnpm", "yarn", "ruff", "mypy", '
    '"eslint", "tsc", "python", "node"]'
)


def upgrade() -> None:
    """Add project policy fields and durable approval records."""
    op.add_column(
        "projects",
        sa.Column(
            "approval_mode",
            sa.String(),
            nullable=False,
            server_default="RISKY",
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "command_allowlist",
            sa.JSON(),
            nullable=False,
            server_default=sa.text(f"'{DEFAULT_COMMANDS}'::json"),
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "max_command_seconds",
            sa.Integer(),
            nullable=False,
            server_default="120",
        ),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("instruction_id", sa.String(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["instruction_id"], ["instructions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "project_id",
        "user_id",
        "instruction_id",
        "fingerprint",
        "status",
    ):
        op.create_index(
            f"ix_approval_requests_{column}",
            "approval_requests",
            [column],
        )


def downgrade() -> None:
    """Remove approval workflows and project command policy."""
    for column in (
        "status",
        "fingerprint",
        "instruction_id",
        "user_id",
        "project_id",
    ):
        op.drop_index(
            f"ix_approval_requests_{column}",
            table_name="approval_requests",
        )
    op.drop_table("approval_requests")
    op.drop_column("projects", "max_command_seconds")
    op.drop_column("projects", "command_allowlist")
    op.drop_column("projects", "approval_mode")
