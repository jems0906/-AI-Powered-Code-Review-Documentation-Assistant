"""
Reviews API — list, get, and manage AI code review results.
"""
from typing import Optional
from uuid import UUID
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.review import Review, ReviewComment, ReviewStatus
from app.schemas.review import (
    ReviewResponse,
    ReviewListResponse,
    CommentFeedbackRequest,
    ReviewTriggerRequest,
)
from app.services.review_service import ReviewService

router = APIRouter()
log = structlog.get_logger()


@router.get("/", response_model=ReviewListResponse)
async def list_reviews(
    repo_full_name: Optional[str] = Query(None),
    status: Optional[ReviewStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Review)
        .options(selectinload(Review.comments))
        .order_by(desc(Review.created_at))
        .limit(limit)
        .offset(offset)
    )
    if repo_full_name:
        stmt = stmt.where(Review.repo_full_name == repo_full_name)
    if status:
        stmt = stmt.where(Review.status == status)

    result = await db.execute(stmt)
    reviews = result.scalars().all()

    count_stmt = select(Review)
    if repo_full_name:
        count_stmt = count_stmt.where(Review.repo_full_name == repo_full_name)
    if status:
        count_stmt = count_stmt.where(Review.status == status)
    total = len((await db.execute(count_stmt)).scalars().all())

    return ReviewListResponse(reviews=[ReviewResponse.model_validate(r) for r in reviews], total=total)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.comments))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewResponse.model_validate(review)


@router.post("/trigger", response_model=ReviewResponse, status_code=202)
async def trigger_review(
    body: ReviewTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a review for a PR (useful for testing without a webhook)."""
    service = ReviewService(db)
    review = await service.create_manual_review(body)
    return ReviewResponse.model_validate(review)


@router.post("/comments/{comment_id}/feedback")
async def submit_comment_feedback(
    comment_id: UUID,
    body: CommentFeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject an AI suggestion — used for the feedback loop."""
    result = await db.execute(select(ReviewComment).where(ReviewComment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.feedback = body.feedback
    comment.feedback_note = body.note

    review_result = await db.execute(select(Review).where(Review.id == comment.review_id))
    review = review_result.scalar_one_or_none()
    if review:
        comments_result = await db.execute(
            select(ReviewComment.feedback).where(ReviewComment.review_id == review.id)
        )
        feedback_values = comments_result.scalars().all()
        review.accepted_count = sum(1 for f in feedback_values if str(f) in ("FeedbackType.accepted", "accepted"))
        review.rejected_count = sum(1 for f in feedback_values if str(f) in ("FeedbackType.rejected", "rejected"))

    await db.commit()
    return {"status": "recorded"}
