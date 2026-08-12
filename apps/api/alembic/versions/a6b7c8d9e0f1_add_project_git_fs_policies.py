"""add project git and filesystem policy columns

Revision ID: a6b7c8d9e0f1
Revises: f0a1b2c3d4e5
Create Date: 2026-08-08
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add git authorization and filesystem CRUD policy columns to projects."""
    op.add_column(
        "projects",
        sa.Column("git_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "projects",
        sa.Column(
            "git_branch_patterns",
            sa.JSON(),
            nullable=False,
            server_default='["*"]',
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "git_require_pr", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "projects",
        sa.Column("git_commit_template", sa.Text(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "fs_read_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "fs_write_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "fs_delete_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
    )


def downgrade() -> None:
    """Remove git authorization and filesystem CRUD policy columns."""
    op.drop_column("projects", "fs_delete_enabled")
    op.drop_column("projects", "fs_write_enabled")
    op.drop_column("projects", "fs_read_enabled")
    op.drop_column("projects", "git_commit_template")
    op.drop_column("projects", "git_require_pr")
    op.drop_column("projects", "git_branch_patterns")
    op.drop_column("projects", "git_enabled")
