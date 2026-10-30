"""add case status history table

Revision ID: h2c3d4e5f6a7
Revises: g1b2c3d4e5f6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h2c3d4e5f6a7"
down_revision: Union[str, None] = "g1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["case_reviews.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_status_history_id", "case_status_history", ["id"])
    op.create_index("ix_case_status_history_case_id", "case_status_history", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_case_status_history_case_id", table_name="case_status_history")
    op.drop_index("ix_case_status_history_id", table_name="case_status_history")
    op.drop_table("case_status_history")
