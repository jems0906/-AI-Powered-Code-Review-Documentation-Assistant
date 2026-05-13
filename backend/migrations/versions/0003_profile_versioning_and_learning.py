"""add profile versioning support

Revision ID: 0003_profile_versioning
Revises: 0002_add_generated_tests
Create Date: 2026-05-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_profile_versioning"
down_revision: Union[str, None] = "0002_add_generated_tests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("active_profile_version", sa.Integer(), nullable=True))

    op.create_table(
        "repository_review_profile_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("review_profile", sa.String(32), nullable=False),
        sa.Column("prompt_overrides", sa.Text(), nullable=True),
        sa.Column("learning_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_repository_review_profile_versions_repository_id",
        "repository_review_profile_versions",
        ["repository_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_repository_review_profile_versions_repository_id",
        table_name="repository_review_profile_versions",
    )
    op.drop_table("repository_review_profile_versions")
    op.drop_column("repositories", "active_profile_version")
