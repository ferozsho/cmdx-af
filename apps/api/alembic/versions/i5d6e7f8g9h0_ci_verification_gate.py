"""Add project CI verification gate.

Revision ID: i5d6e7f8g9h0
Revises: h4c5d6e7f8g9
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "i5d6e7f8g9h0"
down_revision: Union[str, None] = "h4c5d6e7f8g9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "ci_gate_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "ci_gate_enabled")
