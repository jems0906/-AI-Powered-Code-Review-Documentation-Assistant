from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.database import get_db
from app.models.repository import Repository, RepositoryReviewProfileVersion
from app.schemas.repository import (
    RepositoryResponse,
    RepositoryReviewProfileUpdate,
    RepositoryReviewProfileVersionCreate,
    RepositoryReviewProfileVersionResponse,
)

router = APIRouter()


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repository).order_by(Repository.full_name))
    return [RepositoryResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repository).where(Repository.github_id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositoryResponse.model_validate(repo)


@router.patch("/{repo_id}/review-profile", response_model=RepositoryResponse)
async def update_repository_review_profile(
    repo_id: int,
    body: RepositoryReviewProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.review_profile = body.review_profile
    await _create_profile_version(db, repo.id, body.review_profile)
    await db.commit()
    await db.refresh(repo)
    return RepositoryResponse.model_validate(repo)


@router.get("/{repo_id}/review-profiles", response_model=list[RepositoryReviewProfileVersionResponse])
async def list_repository_review_profiles(repo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RepositoryReviewProfileVersion)
        .where(RepositoryReviewProfileVersion.repository_id == repo_id)
        .order_by(RepositoryReviewProfileVersion.version_number.desc())
    )
    return [RepositoryReviewProfileVersionResponse.model_validate(v) for v in result.scalars().all()]


@router.post("/{repo_id}/review-profiles", response_model=RepositoryReviewProfileVersionResponse, status_code=201)
async def create_repository_review_profile_version(
    repo_id: int,
    body: RepositoryReviewProfileVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    repo = (await db.execute(select(Repository).where(Repository.id == repo_id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    version = await _create_profile_version(
        db,
        repository_id=repo_id,
        review_profile=body.review_profile,
        prompt_overrides=body.prompt_overrides,
    )
    repo.review_profile = body.review_profile
    repo.active_profile_version = version.version_number
    await db.commit()
    await db.refresh(version)
    return RepositoryReviewProfileVersionResponse.model_validate(version)


@router.post("/{repo_id}/review-profiles/{version_id}/activate", response_model=RepositoryResponse)
async def activate_repository_review_profile_version(
    repo_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
):
    repo = (await db.execute(select(Repository).where(Repository.id == repo_id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    version = (
        await db.execute(
            select(RepositoryReviewProfileVersion)
            .where(RepositoryReviewProfileVersion.id == version_id)
            .where(RepositoryReviewProfileVersion.repository_id == repo_id)
        )
    ).scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Profile version not found")

    await db.execute(
        update(RepositoryReviewProfileVersion)
        .where(RepositoryReviewProfileVersion.repository_id == repo_id)
        .values(is_active=False)
    )
    version.is_active = True
    repo.review_profile = version.review_profile
    repo.active_profile_version = version.version_number
    await db.commit()
    await db.refresh(repo)
    return RepositoryResponse.model_validate(repo)


async def _create_profile_version(
    db: AsyncSession,
    repository_id: int,
    review_profile: str,
    prompt_overrides: str | None = None,
) -> RepositoryReviewProfileVersion:
    max_version = (
        await db.execute(
            select(func.max(RepositoryReviewProfileVersion.version_number))
            .where(RepositoryReviewProfileVersion.repository_id == repository_id)
        )
    ).scalar_one_or_none()
    next_version = (max_version or 0) + 1

    await db.execute(
        update(RepositoryReviewProfileVersion)
        .where(RepositoryReviewProfileVersion.repository_id == repository_id)
        .values(is_active=False)
    )

    version = RepositoryReviewProfileVersion(
        repository_id=repository_id,
        version_number=next_version,
        review_profile=review_profile,
        prompt_overrides=prompt_overrides,
        is_active=True,
    )
    db.add(version)
    return version
