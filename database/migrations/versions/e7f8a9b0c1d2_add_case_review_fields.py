"""add case review fields

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columns introduced on the ORM CaseReview model after initial schema.
    op.add_column("case_reviews", sa.Column("priority", sa.String(length=50), nullable=False, server_default="MEDIUM"))
    op.add_column("case_reviews", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column("case_reviews", sa.Column("due_date", sa.DateTime(), nullable=True))
    op.add_column("case_reviews", sa.Column("created_by", sa.Integer(), nullable=True))
    op.create_index("ix_case_reviews_priority", "case_reviews", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_case_reviews_priority", table_name="case_reviews")
    op.drop_column("case_reviews", "created_by")
    op.drop_column("case_reviews", "due_date")
    op.drop_column("case_reviews", "resolution_notes")
    op.drop_column("case_reviews", "priority")
