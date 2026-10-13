from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RequirementTask(Base):
    __tablename__ = "requirement_tasks"

    requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    def __repr__(self) -> str:
        return f"RequirementTask(requirement_id={self.requirement_id!r}, task_id={self.task_id!r})"


__all__ = ["RequirementTask"]
