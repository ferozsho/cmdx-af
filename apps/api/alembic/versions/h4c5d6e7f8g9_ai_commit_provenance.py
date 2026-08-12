"""Add durable AI commit provenance.

Revision ID: h4c5d6e7f8g9
Revises: g3b4c5d6e7f8
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "h4c5d6e7f8g9"
down_revision: Union[str, None] = "g3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("git_commits", sa.Column("project_id", sa.String(), nullable=True))
    op.add_column("git_commits", sa.Column("user_id", sa.String(), nullable=True))
    op.add_column(
        "git_commits",
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "git_commits", sa.Column("provenance_digest", sa.String(64), nullable=True)
    )
    op.add_column(
        "git_commits", sa.Column("prompt_digest", sa.String(64), nullable=True)
    )
    op.add_column("git_commits", sa.Column("model_name", sa.String(), nullable=True))
    op.add_column(
        "git_commits",
        sa.Column("changed_files", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "git_commits",
        sa.Column("commit_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "git_commits",
        sa.Column(
            "verification_status",
            sa.String(),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.create_foreign_key(
        "fk_git_commits_project_id_projects",
        "git_commits",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_git_commits_user_id_users",
        "git_commits",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_git_commits_project_id", "git_commits", ["project_id"])
    op.create_index("ix_git_commits_user_id", "git_commits", ["user_id"])
    op.create_index(
        "ix_git_commits_provenance_digest", "git_commits", ["provenance_digest"]
    )


def downgrade() -> None:
    op.drop_index("ix_git_commits_provenance_digest", table_name="git_commits")
    op.drop_index("ix_git_commits_user_id", table_name="git_commits")
    op.drop_index("ix_git_commits_project_id", table_name="git_commits")
    op.drop_constraint(
        "fk_git_commits_user_id_users", "git_commits", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_git_commits_project_id_projects", "git_commits", type_="foreignkey"
    )
    for column in (
        "verification_status",
        "commit_metadata",
        "changed_files",
        "model_name",
        "prompt_digest",
        "provenance_digest",
        "ai_generated",
        "user_id",
        "project_id",
    ):
        op.drop_column("git_commits", column)
