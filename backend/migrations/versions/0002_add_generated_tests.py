"""add generated_tests column to reviews

Revision ID: 0002_add_generated_tests
Revises: 0001_initial
Create Date: 2026-05-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_generated_tests"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reviews", sa.Column("generated_tests", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("reviews", "generated_tests")
