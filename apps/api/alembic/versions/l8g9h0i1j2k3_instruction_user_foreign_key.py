"""Enforce instruction ownership referential integrity.

Revision ID: l8g9h0i1j2k3
Revises: k7f8g9h0i1j2
"""

from typing import Sequence, Union

from alembic import op

revision: str = "l8g9h0i1j2k3"
down_revision: Union[str, None] = "k7f8g9h0i1j2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Link nullable instruction owners to users without losing history."""
    op.create_foreign_key(
        "fk_instructions_user_id_users",
        "instructions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove instruction-owner referential enforcement."""
    op.drop_constraint(
        "fk_instructions_user_id_users",
        "instructions",
        type_="foreignkey",
    )
