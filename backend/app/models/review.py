import uuid
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Float, Text, ForeignKey, Enum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class SeverityLevel(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class CommentCategory(str, enum.Enum):
    security = "security"
    performance = "performance"
    best_practice = "best_practice"
    edge_case = "edge_case"
    documentation = "documentation"
    style = "style"


class FeedbackType(str, enum.Enum):
    accepted = "accepted"
    rejected = "rejected"
    partial = "partial"


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_full_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[str] = mapped_column(String(512), nullable=True)
    pr_author: Mapped[str] = mapped_column(String(128), nullable=True)
    pr_url: Mapped[str] = mapped_column(String(512), nullable=True)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.pending, index=True)
    review_profile: Mapped[str] = mapped_column(String(32), default="balanced")
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_docs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_tests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    extra_meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    comments: Mapped[List["ReviewComment"]] = relationship(
        "ReviewComment", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[CommentCategory] = mapped_column(Enum(CommentCategory), nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[FeedbackType]] = mapped_column(Enum(FeedbackType), nullable=True)
    feedback_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    review: Mapped["Review"] = relationship("Review", back_populates="comments")
