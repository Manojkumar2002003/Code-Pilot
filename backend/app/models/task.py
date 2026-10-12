from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Task(Base):
    __tablename__ = "tasks"

    __table_args__ = (
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'completed', 'blocked', 'cancelled')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_tasks_priority",
        ),
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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
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

    project: Mapped[Project] = relationship("Project", back_populates="tasks")

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Task title cannot be empty.")
        return cleaned

    @validates("description")
    def validate_description(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned if cleaned else None

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        normalized = str(value).strip().lower()
        valid_statuses = {"todo", "in_progress", "completed", "blocked", "cancelled"}
        if normalized not in valid_statuses:
            raise ValueError(f"Task status must be one of: {sorted(valid_statuses)}")
        return normalized

    @validates("priority")
    def validate_priority(self, key: str, value: str) -> str:
        normalized = str(value).strip().lower()
        valid_priorities = {"low", "medium", "high", "critical"}
        if normalized not in valid_priorities:
            raise ValueError(f"Task priority must be one of: {sorted(valid_priorities)}")
        return normalized

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "created_at" not in kwargs:
            kwargs["created_at"] = utc_now()
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = kwargs["created_at"]
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, project_id={self.project_id!r})"


__all__ = ["Task"]
