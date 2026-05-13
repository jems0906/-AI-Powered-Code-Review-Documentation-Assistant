"""
GitHub webhook endpoint — receives PR events and triggers analysis.
"""
import hashlib
import hmac
import json
import structlog

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.config import settings
from app.core.database import get_db
from app.services.review_service import ReviewService

router = APIRouter()
log = structlog.get_logger()


def _verify_github_signature(payload: bytes, signature: str) -> bool:
    """HMAC-SHA256 verification of GitHub webhook payload."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def _verify_gitlab_token(token: str) -> bool:
    return bool(token) and token == settings.GITLAB_WEBHOOK_SECRET


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
):
    payload_bytes = await request.body()

    if not _verify_github_signature(payload_bytes, x_hub_signature_256):
        log.warning("Invalid GitHub webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    log.info("Received GitHub webhook", event=x_github_event)

    if x_github_event == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            pr_data = payload.get("pull_request", {})
            repo_data = payload.get("repository", {})
            background_tasks.add_task(
                _handle_pr_event,
                db,
                pr_data,
                repo_data,
            )

    return {"received": True}


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_gitlab_token: str = Header(default=""),
    x_gitlab_event: str = Header(default=""),
):
    if not _verify_gitlab_token(x_gitlab_token):
        log.warning("Invalid GitLab webhook token")
        raise HTTPException(status_code=401, detail="Invalid token")

    payload = await request.json()
    log.info("Received GitLab webhook", event=x_gitlab_event)

    if x_gitlab_event == "Merge Request Hook":
        attrs = payload.get("object_attributes", {})
        action = attrs.get("action", "")
        if action in ("open", "update", "reopen"):
            project_data = payload.get("project", {})
            mr_data = {
                "iid": attrs.get("iid"),
                "title": attrs.get("title"),
                "url": attrs.get("url"),
                "web_url": attrs.get("url"),
                "last_commit": attrs.get("last_commit", {}),
                "author": payload.get("user", {}),
            }
            background_tasks.add_task(_handle_gitlab_mr_event, db, mr_data, project_data)

    return {"received": True}


async def _handle_pr_event(db: AsyncSession, pr_data: dict, repo_data: dict):
    service = ReviewService(db)
    await service.process_pull_request(pr_data, repo_data)


async def _handle_gitlab_mr_event(db: AsyncSession, mr_data: dict, project_data: dict):
    service = ReviewService(db)
    await service.process_gitlab_merge_request(mr_data, project_data)
