from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Requirement(Base):
    __tablename__ = "requirements"

    __table_args__ = (
        CheckConstraint("type IN ('functional', 'non_functional')", name="ck_requirements_type"),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name="ck_requirements_priority"),
        CheckConstraint("status IN ('draft', 'approved', 'rejected')", name="ck_requirements_status"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="functional")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Requirement title cannot be empty.")
        return cleaned

    @validates("description")
    def validate_description(self, key: str, value: str) -> str:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Requirement description cannot be empty.")
        return cleaned

    @validates("type")
    def validate_type(self, key: str, value: str) -> str:
        normalized = str(value).strip().lower()
        valid_types = {"functional", "non_functional"}
        if normalized not in valid_types:
            raise ValueError(f"Requirement type must be one of: {sorted(valid_types)}")
        return normalized

    @validates("priority")
    def validate_priority(self, key: str, value: str) -> str:
        normalized = str(value).strip().lower()
        valid_priorities = {"low", "medium", "high", "critical"}
        if normalized not in valid_priorities:
            raise ValueError(f"Requirement priority must be one of: {sorted(valid_priorities)}")
        return normalized

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        normalized = str(value).strip().lower()
        valid_statuses = {"draft", "approved", "rejected"}
        if normalized not in valid_statuses:
            raise ValueError(f"Requirement status must be one of: {sorted(valid_statuses)}")
        return normalized

    def __init__(self, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "created_at" not in kwargs:
            kwargs["created_at"] = utc_now()
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = kwargs["created_at"]
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"Requirement(id={self.id!r}, title={self.title!r})"

