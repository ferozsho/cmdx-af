"""Cascade instruction event cleanup with its owning records.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make event journal rows follow instruction and project deletion."""
    op.drop_constraint(
        "instruction_events_instruction_id_fkey",
        "instruction_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instruction_events_project_id_fkey",
        "instruction_events",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "instruction_events_instruction_id_fkey",
        "instruction_events",
        "instructions",
        ["instruction_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instruction_events_project_id_fkey",
        "instruction_events",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Restore restrictive event journal foreign keys."""
    op.drop_constraint(
        "instruction_events_instruction_id_fkey",
        "instruction_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instruction_events_project_id_fkey",
        "instruction_events",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "instruction_events_instruction_id_fkey",
        "instruction_events",
        "instructions",
        ["instruction_id"],
        ["id"],
    )
    op.create_foreign_key(
        "instruction_events_project_id_fkey",
        "instruction_events",
        "projects",
        ["project_id"],
        ["id"],
    )
