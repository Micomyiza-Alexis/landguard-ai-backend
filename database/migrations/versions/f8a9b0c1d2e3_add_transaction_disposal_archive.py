"""add transaction disposal and archive state

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("is_disposable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "transactions",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("transactions", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("transactions", sa.Column("archived_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_archived_by_users",
        "transactions",
        "users",
        ["archived_by"],
        ["id"],
    )
    op.create_index("ix_transactions_is_disposable", "transactions", ["is_disposable"])
    op.create_index("ix_transactions_is_archived", "transactions", ["is_archived"])
    op.alter_column("transactions", "is_disposable", server_default=None)
    op.alter_column("transactions", "is_archived", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_transactions_is_archived", table_name="transactions")
    op.drop_index("ix_transactions_is_disposable", table_name="transactions")
    op.drop_constraint("fk_transactions_archived_by_users", "transactions", type_="foreignkey")
    op.drop_column("transactions", "archived_by")
    op.drop_column("transactions", "archived_at")
    op.drop_column("transactions", "is_archived")
    op.drop_column("transactions", "is_disposable")
