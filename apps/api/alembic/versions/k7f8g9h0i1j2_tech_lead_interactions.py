"""Add audited tech lead interactions.

Revision ID: k7f8g9h0i1j2
Revises: j6e7f8g9h0i1
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "k7f8g9h0i1j2"
down_revision: Union[str, None] = "j6e7f8g9h0i1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tech_lead_interactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tech_lead_interactions_project_id",
        "tech_lead_interactions",
        ["project_id"],
    )
    op.create_index(
        "ix_tech_lead_interactions_user_id",
        "tech_lead_interactions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tech_lead_interactions_user_id",
        table_name="tech_lead_interactions",
    )
    op.drop_index(
        "ix_tech_lead_interactions_project_id",
        table_name="tech_lead_interactions",
    )
    op.drop_table("tech_lead_interactions")
