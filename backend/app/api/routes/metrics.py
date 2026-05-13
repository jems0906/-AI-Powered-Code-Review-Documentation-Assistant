from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from io import StringIO
import csv
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from app.core.database import get_db
from app.models.review import Review, ReviewComment
from app.schemas.metrics import MetricsSummary, TrendPoint, EngineerMetric, FeedbackLearningSignal

router = APIRouter()


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    repo_full_name: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Review)
    if repo_full_name:
        stmt = stmt.where(Review.repo_full_name == repo_full_name)
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    total_reviews = len(reviews)
    total_comments = sum(r.comment_count for r in reviews)
    accepted = sum(1 for r in reviews if r.accepted_count)
    avg_quality = (
        sum(r.quality_score for r in reviews if r.quality_score) / total_reviews
        if total_reviews else 0
    )

    return MetricsSummary(
        total_reviews=total_reviews,
        total_comments=total_comments,
        acceptance_rate=accepted / total_reviews if total_reviews else 0,
        avg_quality_score=round(avg_quality, 2),
    )


@router.get("/trends", response_model=list[TrendPoint])
async def get_quality_trends(
    repo_full_name: str = Query(None),
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(
        func.date_trunc("day", Review.created_at).label("day"),
        func.avg(Review.quality_score).label("avg_quality"),
        func.count(Review.id).label("count"),
    ).group_by("day").order_by("day")

    if repo_full_name:
        stmt = stmt.where(Review.repo_full_name == repo_full_name)

    result = await db.execute(stmt)
    rows = result.all()
    return [TrendPoint(date=str(r.day), avg_quality=round(r.avg_quality or 0, 2), count=r.count) for r in rows]


@router.get("/export")
async def export_metrics(
    repo_full_name: str = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(
        Review.repo_full_name,
        Review.pr_number,
        Review.status,
        Review.review_profile,
        Review.quality_score,
        Review.comment_count,
        Review.accepted_count,
        Review.rejected_count,
        Review.ai_provider,
        Review.created_at,
        Review.completed_at,
    ).order_by(Review.created_at.desc())

    if repo_full_name:
        stmt = stmt.where(Review.repo_full_name == repo_full_name)

    rows = (await db.execute(stmt)).all()
    payload = [
        {
            "repo_full_name": r.repo_full_name,
            "pr_number": r.pr_number,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "review_profile": r.review_profile,
            "quality_score": r.quality_score,
            "comment_count": r.comment_count,
            "accepted_count": r.accepted_count,
            "rejected_count": r.rejected_count,
            "ai_provider": r.ai_provider,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]

    if format == "csv":
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "repo_full_name",
                "pr_number",
                "status",
                "review_profile",
                "quality_score",
                "comment_count",
                "accepted_count",
                "rejected_count",
                "ai_provider",
                "created_at",
                "completed_at",
            ],
        )
        writer.writeheader()
        writer.writerows(payload)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=review-metrics.csv"},
        )

    return payload


@router.get("/engineers", response_model=list[EngineerMetric])
async def get_engineer_improvements(
    repo_full_name: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Review).where(Review.pr_author.is_not(None))
    if repo_full_name:
        stmt = stmt.where(Review.repo_full_name == repo_full_name)

    reviews = (await db.execute(stmt)).scalars().all()
    if not reviews:
        return []

    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=30)
    previous_cutoff = now - timedelta(days=60)

    quality_by_engineer = defaultdict(list)
    recent_by_engineer = defaultdict(list)
    previous_by_engineer = defaultdict(list)

    for review in reviews:
        author = review.pr_author or "unknown"
        if review.quality_score is not None:
            quality_by_engineer[author].append(review.quality_score)
            if review.created_at and review.created_at >= recent_cutoff:
                recent_by_engineer[author].append(review.quality_score)
            elif review.created_at and previous_cutoff <= review.created_at < recent_cutoff:
                previous_by_engineer[author].append(review.quality_score)

    feedback_stmt = select(Review.pr_author, ReviewComment.feedback).join(
        ReviewComment, ReviewComment.review_id == Review.id
    )
    if repo_full_name:
        feedback_stmt = feedback_stmt.where(Review.repo_full_name == repo_full_name)
    feedback_rows = (await db.execute(feedback_stmt)).all()

    accepted = defaultdict(int)
    rejected = defaultdict(int)
    for author, feedback in feedback_rows:
        key = author or "unknown"
        if str(feedback) in ("FeedbackType.accepted", "accepted"):
            accepted[key] += 1
        elif str(feedback) in ("FeedbackType.rejected", "rejected"):
            rejected[key] += 1

    results: list[EngineerMetric] = []
    for engineer, scores in quality_by_engineer.items():
        avg_quality = sum(scores) / len(scores) if scores else 0
        recent_scores = recent_by_engineer.get(engineer, [])
        prev_scores = previous_by_engineer.get(engineer, [])
        recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        prev_avg = sum(prev_scores) / len(prev_scores) if prev_scores else 0
        accepted_count = accepted.get(engineer, 0)
        rejected_count = rejected.get(engineer, 0)
        denom = accepted_count + rejected_count
        acceptance_rate = accepted_count / denom if denom else 0

        results.append(
            EngineerMetric(
                engineer=engineer,
                total_reviews=len(scores),
                avg_quality_score=round(avg_quality, 2),
                recent_30d_quality=round(recent_avg, 2),
                previous_30d_quality=round(prev_avg, 2),
                quality_delta=round(recent_avg - prev_avg, 2),
                acceptance_rate=round(acceptance_rate, 3),
            )
        )

    results.sort(key=lambda r: (r.quality_delta, r.avg_quality_score), reverse=True)
    return results


@router.get("/learning-feedback", response_model=list[FeedbackLearningSignal])
async def get_feedback_learning_signals(
    repo_full_name: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ReviewComment.category, ReviewComment.feedback, func.count(ReviewComment.id))
        .join(Review, ReviewComment.review_id == Review.id)
        .where(ReviewComment.feedback.is_not(None))
        .group_by(ReviewComment.category, ReviewComment.feedback)
    )
    if repo_full_name:
        stmt = stmt.where(Review.repo_full_name == repo_full_name)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    stats = defaultdict(lambda: {"accepted": 0, "rejected": 0})
    for category, feedback, count in rows:
        category_key = category.value if hasattr(category, "value") else str(category)
        if str(feedback) in ("FeedbackType.accepted", "accepted"):
            stats[category_key]["accepted"] += count
        elif str(feedback) in ("FeedbackType.rejected", "rejected"):
            stats[category_key]["rejected"] += count

    payload = []
    for category, values in stats.items():
        total = values["accepted"] + values["rejected"]
        payload.append(
            FeedbackLearningSignal(
                category=category,
                accepted=values["accepted"],
                rejected=values["rejected"],
                acceptance_rate=(values["accepted"] / total) if total else 0,
            )
        )
    payload.sort(key=lambda x: x.acceptance_rate, reverse=True)
    return payload
