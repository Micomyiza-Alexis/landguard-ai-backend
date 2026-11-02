"""add transaction supporting reference

Revision ID: i3d4e5f6a7b8
Revises: h2c3d4e5f6a7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i3d4e5f6a7b8"
down_revision: Union[str, None] = "h2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("supporting_reference", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "supporting_reference")
