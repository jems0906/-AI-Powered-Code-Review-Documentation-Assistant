from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(64), default="main")
    language: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    review_profile: Mapped[str] = mapped_column(String(32), default="balanced")
    active_profile_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    profile_versions: Mapped[List["RepositoryReviewProfileVersion"]] = relationship(
        "RepositoryReviewProfileVersion",
        back_populates="repository",
        cascade="all, delete-orphan",
    )


class RepositoryReviewProfileVersion(Base):
    __tablename__ = "repository_review_profile_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    review_profile: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_overrides: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    learning_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship("Repository", back_populates="profile_versions")
