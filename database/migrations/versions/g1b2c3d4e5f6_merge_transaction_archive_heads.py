"""merge transaction archive and user session migration heads

Revision ID: g1b2c3d4e5f6
Revises: c2d3e4f5a6b7, f8a9b0c1d2e3
"""
from typing import Sequence, Union


revision: str = "g1b2c3d4e5f6"
down_revision: Union[str, tuple[str, str], None] = (
    "c2d3e4f5a6b7",
    "f8a9b0c1d2e3",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
