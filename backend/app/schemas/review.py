from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic import Field

from app.models.review import ReviewStatus, SeverityLevel, CommentCategory, FeedbackType


class ReviewCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_path: str
    line_start: Optional[int]
    line_end: Optional[int]
    category: CommentCategory
    severity: SeverityLevel
    body: str
    suggested_fix: Optional[str]
    suggested_diff: Optional[str]
    feedback: Optional[FeedbackType]
    created_at: datetime


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repo_full_name: str
    pr_number: int
    pr_title: Optional[str]
    pr_author: Optional[str]
    pr_url: Optional[str]
    status: ReviewStatus
    review_profile: str
    quality_score: Optional[float]
    comment_count: int
    accepted_count: int
    rejected_count: int
    summary: Optional[str]
    generated_docs: Optional[str]
    generated_tests: Optional[str]
    ai_provider: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    comments: List[ReviewCommentResponse] = Field(default_factory=list)


class ReviewListResponse(BaseModel):
    reviews: List[ReviewResponse]
    total: int


class CommentFeedbackRequest(BaseModel):
    feedback: FeedbackType
    note: Optional[str] = None


class ReviewTriggerRequest(BaseModel):
    repo_full_name: str
    pr_number: int
    review_profile: str = "balanced"
