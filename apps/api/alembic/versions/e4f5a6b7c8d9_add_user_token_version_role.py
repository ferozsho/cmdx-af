"""add token_version and role to users

Revision ID: e4f5a6b7c8d9
Revises: c7d8e9f0a1b2
Create Date: 2026-08-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add token_version (JWT revocation) and role (RBAC) to users."""
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(),
            nullable=False,
            server_default="user",
        ),
    )
    # The seeded admin account is the platform admin
    op.execute(
        "UPDATE users SET role = 'admin' "
        "WHERE email = 'admin@agentforge.ai'"
    )


def downgrade() -> None:
    """Drop the new columns."""
    op.drop_column("users", "role")
    op.drop_column("users", "token_version")
