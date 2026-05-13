from pydantic import BaseModel, ConfigDict
from typing import Literal
from datetime import datetime
from typing import Optional


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    github_id: int
    full_name: str
    owner: str
    name: str
    default_branch: str
    language: Optional[str]
    review_profile: str
    active_profile_version: Optional[int]
    created_at: datetime


class RepositoryReviewProfileUpdate(BaseModel):
    review_profile: Literal["pedantic", "balanced", "relaxed"]


class RepositoryReviewProfileVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    version_number: int
    review_profile: Literal["pedantic", "balanced", "relaxed"]
    prompt_overrides: Optional[str]
    learning_snapshot: Optional[dict]
    is_active: bool
    created_at: datetime


class RepositoryReviewProfileVersionCreate(BaseModel):
    review_profile: Literal["pedantic", "balanced", "relaxed"]
    prompt_overrides: Optional[str] = None
