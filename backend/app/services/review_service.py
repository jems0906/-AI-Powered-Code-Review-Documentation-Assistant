"""
ReviewService — orchestrates PR ingestion → code analysis → AI review → DB persistence.
"""
from collections import defaultdict
import structlog
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.review import Review, ReviewComment, ReviewStatus
from app.models.repository import Repository
from app.schemas.review import ReviewTriggerRequest
from app.analysis.engine import CodeAnalysisEngine
from app.ai.reviewer import AIReviewer
from app.integrations.github_client import GitHubClient
from app.integrations.gitlab_client import GitLabClient
from app.integrations.slack_client import SlackClient

log = structlog.get_logger()


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analysis_engine = CodeAnalysisEngine()
        self.ai_reviewer = AIReviewer()
        self.github = GitHubClient()
        self.gitlab = GitLabClient()
        self.slack = SlackClient()

    async def process_pull_request(self, pr_data: dict, repo_data: dict):
        repo_full_name = repo_data.get("full_name", "")
        pr_number = pr_data.get("number", 0)
        log.info("Processing PR", repo=repo_full_name, pr=pr_number)

        # Upsert repository
        repo = await self._upsert_repository(repo_data)

        # Create review record
        review = Review(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            pr_title=pr_data.get("title"),
            pr_author=pr_data.get("user", {}).get("login"),
            pr_url=pr_data.get("html_url"),
            head_sha=pr_data.get("head", {}).get("sha"),
            status=ReviewStatus.in_progress,
            review_profile=repo.review_profile if repo else "balanced",
        )
        self.db.add(review)
        await self.db.flush()

        try:
            # Fetch diff from GitHub
            diff_text = await self.github.get_pr_diff(repo_full_name, pr_number)
            review.raw_diff = diff_text

            # Static analysis
            analysis_result = self.analysis_engine.analyze_diff(diff_text)
            feedback_learning_context = await self._build_feedback_learning_context(repo_full_name)

            # AI review
            ai_result = await self.ai_reviewer.review(
                diff=diff_text,
                analysis=analysis_result,
                profile=review.review_profile,
                repository_language=repo.language if repo else None,
                feedback_learning_context=feedback_learning_context,
            )

            # Persist comments
            for c in ai_result.comments:
                comment = ReviewComment(
                    review_id=review.id,
                    file_path=c.file_path,
                    line_start=c.line_start,
                    line_end=c.line_end,
                    category=c.category,
                    severity=c.severity,
                    body=c.body,
                    suggested_fix=c.suggested_fix,
                    suggested_diff=c.suggested_diff,
                )
                self.db.add(comment)

            review.comment_count = len(ai_result.comments)
            review.quality_score = ai_result.quality_score
            review.summary = ai_result.summary
            review.generated_docs = ai_result.generated_docs
            review.generated_tests = ai_result.generated_tests
            review.ai_provider = ai_result.provider
            review.status = ReviewStatus.completed
            review.completed_at = datetime.now(timezone.utc)

            # Post review back to GitHub PR
            await self.github.post_review(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=review.head_sha,
                summary=ai_result.summary,
                comments=ai_result.comments,
            )

            # Slack notification for critical issues
            critical = [c for c in ai_result.comments if c.severity in ("critical", "high")]
            if critical:
                await self.slack.notify_critical_issues(
                    repo=repo_full_name,
                    pr_number=pr_number,
                    pr_url=review.pr_url,
                    issues=critical,
                )

        except Exception as exc:
            log.error("Review failed", error=str(exc), repo=repo_full_name, pr=pr_number)
            review.status = ReviewStatus.failed
            raise
        finally:
            await self.db.commit()

    async def create_manual_review(self, req: ReviewTriggerRequest) -> Review:
        pr_data = await self.github.get_pr(req.repo_full_name, req.pr_number)
        repo_data = {"full_name": req.repo_full_name, "id": 0, "owner": {"login": req.repo_full_name.split("/")[0]}, "name": req.repo_full_name.split("/")[1], "default_branch": "main"}
        await self.process_pull_request(pr_data, repo_data)
        result = await self.db.execute(
            select(Review)
            .where(Review.repo_full_name == req.repo_full_name)
            .where(Review.pr_number == req.pr_number)
            .order_by(Review.created_at.desc())
        )
        return result.scalar_one()

    async def process_gitlab_merge_request(self, mr_data: dict, project_data: dict):
        project_full_name = project_data.get("path_with_namespace", "")
        mr_iid = mr_data.get("iid", 0)
        project_id = project_data.get("id", 0)
        log.info("Processing GitLab MR", project=project_full_name, mr=mr_iid)

        # Use negative provider ID to avoid collisions with GitHub ids.
        repository_data = {
            "id": -abs(int(project_id)) if project_id else 0,
            "full_name": project_full_name,
            "owner": {"login": (project_full_name.split("/")[0] if "/" in project_full_name else "")},
            "name": (project_full_name.split("/")[-1] if project_full_name else ""),
            "default_branch": project_data.get("default_branch", "main"),
            "language": project_data.get("programming_language"),
        }

        repo = await self._upsert_repository(repository_data)

        review = Review(
            repo_full_name=project_full_name,
            pr_number=mr_iid,
            pr_title=mr_data.get("title"),
            pr_author=mr_data.get("last_commit", {}).get("author", {}).get("name") or mr_data.get("author", {}).get("username"),
            pr_url=mr_data.get("url") or mr_data.get("web_url"),
            head_sha=mr_data.get("last_commit", {}).get("id"),
            status=ReviewStatus.in_progress,
            review_profile=repo.review_profile if repo else "balanced",
        )
        self.db.add(review)
        await self.db.flush()

        try:
            diff_text = await self.gitlab.get_merge_request_diff(project_id, mr_iid)
            review.raw_diff = diff_text

            analysis_result = self.analysis_engine.analyze_diff(diff_text)
            feedback_learning_context = await self._build_feedback_learning_context(project_full_name)
            ai_result = await self.ai_reviewer.review(
                diff=diff_text,
                analysis=analysis_result,
                profile=review.review_profile,
                repository_language=repo.language if repo else None,
                feedback_learning_context=feedback_learning_context,
            )

            for c in ai_result.comments:
                comment = ReviewComment(
                    review_id=review.id,
                    file_path=c.file_path,
                    line_start=c.line_start,
                    line_end=c.line_end,
                    category=c.category,
                    severity=c.severity,
                    body=c.body,
                    suggested_fix=c.suggested_fix,
                    suggested_diff=c.suggested_diff,
                )
                self.db.add(comment)

            review.comment_count = len(ai_result.comments)
            review.quality_score = ai_result.quality_score
            review.summary = ai_result.summary
            review.generated_docs = ai_result.generated_docs
            review.generated_tests = ai_result.generated_tests
            review.ai_provider = ai_result.provider
            review.status = ReviewStatus.completed
            review.completed_at = datetime.now(timezone.utc)

            await self.gitlab.post_merge_request_note(
                project_id=project_id,
                mr_iid=mr_iid,
                body=ai_result.summary,
            )

            critical = [c for c in ai_result.comments if c.severity in ("critical", "high")]
            if critical:
                await self.slack.notify_critical_issues(
                    repo=project_full_name,
                    pr_number=mr_iid,
                    pr_url=review.pr_url,
                    issues=critical,
                )

        except Exception as exc:
            log.error("GitLab review failed", error=str(exc), project=project_full_name, mr=mr_iid)
            review.status = ReviewStatus.failed
            raise
        finally:
            await self.db.commit()

    async def _upsert_repository(self, repo_data: dict) -> Repository:
        github_id = repo_data.get("id", 0)
        result = await self.db.execute(select(Repository).where(Repository.github_id == github_id))
        repo = result.scalar_one_or_none()
        if not repo:
            repo = Repository(
                github_id=github_id,
                full_name=repo_data.get("full_name", ""),
                owner=repo_data.get("owner", {}).get("login", ""),
                name=repo_data.get("name", ""),
                default_branch=repo_data.get("default_branch", "main"),
                language=repo_data.get("language"),
            )
            self.db.add(repo)
            await self.db.flush()
        return repo

    async def _build_feedback_learning_context(self, repo_full_name: str) -> str:
        result = await self.db.execute(
            select(ReviewComment.category, ReviewComment.feedback)
            .join(Review, ReviewComment.review_id == Review.id)
            .where(Review.repo_full_name == repo_full_name)
            .where(ReviewComment.feedback.is_not(None))
        )
        rows = result.all()
        if not rows:
            return "No prior developer feedback available."

        accepted = defaultdict(int)
        rejected = defaultdict(int)
        for category, feedback in rows:
            category_key = category.value if hasattr(category, "value") else str(category)
            if str(feedback) == "FeedbackType.accepted" or str(feedback) == "accepted":
                accepted[category_key] += 1
            elif str(feedback) == "FeedbackType.rejected" or str(feedback) == "rejected":
                rejected[category_key] += 1

        accepted_sorted = sorted(accepted.items(), key=lambda x: x[1], reverse=True)
        rejected_sorted = sorted(rejected.items(), key=lambda x: x[1], reverse=True)

        accepted_text = ", ".join(f"{k} ({v})" for k, v in accepted_sorted[:3]) or "none"
        rejected_text = ", ".join(f"{k} ({v})" for k, v in rejected_sorted[:3]) or "none"
        return (
            f"Commonly accepted categories: {accepted_text}. "
            f"Commonly rejected categories: {rejected_text}. "
            "Prioritize high-signal categories and avoid repeatedly rejected low-value suggestions."
        )
