"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("default_branch", sa.String(64), nullable=False, server_default="main"),
        sa.Column("language", sa.String(64), nullable=True),
        sa.Column("review_profile", sa.String(32), nullable=False, server_default="balanced"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_id"),
        sa.UniqueConstraint("full_name"),
    )

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repo_full_name", sa.String(256), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pr_title", sa.String(512), nullable=True),
        sa.Column("pr_author", sa.String(128), nullable=True),
        sa.Column("pr_url", sa.String(512), nullable=True),
        sa.Column("head_sha", sa.String(64), nullable=True),
        sa.Column("status", sa.Enum("pending", "in_progress", "completed", "failed", name="reviewstatus"), nullable=False, server_default="pending"),
        sa.Column("review_profile", sa.String(32), nullable=False, server_default="balanced"),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("generated_docs", sa.Text(), nullable=True),
        sa.Column("raw_diff", sa.Text(), nullable=True),
        sa.Column("ai_provider", sa.String(32), nullable=True),
        sa.Column("extra_meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_repo_full_name", "reviews", ["repo_full_name"])
    op.create_index("ix_reviews_status", "reviews", ["status"])

    op.create_table(
        "review_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("category", sa.Enum("security", "performance", "best_practice", "edge_case", "documentation", "style", name="commentcategory"), nullable=False),
        sa.Column("severity", sa.Enum("critical", "high", "medium", "low", "info", name="severitylevel"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("suggested_diff", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Enum("accepted", "rejected", "partial", name="feedbacktype"), nullable=True),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_comments_review_id", "review_comments", ["review_id"])


def downgrade() -> None:
    op.drop_table("review_comments")
    op.drop_table("reviews")
    op.drop_table("repositories")
    op.execute("DROP TYPE IF EXISTS reviewstatus")
    op.execute("DROP TYPE IF EXISTS commentcategory")
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS feedbacktype")
