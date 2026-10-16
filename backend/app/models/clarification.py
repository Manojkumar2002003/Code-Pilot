from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ClarificationSession(Base):
    """Tracks state, questions, answers, and revisions of a clarification process."""

    __tablename__ = "clarification_sessions"

    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_clarification', 'ready_for_refinement', "
            "'refinement_in_progress', 'completed', 'failed', 'cancelled')",
            name="ck_clarification_sessions_status",
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
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="awaiting_clarification",
    )
    current_revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    original_context: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    questions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    answers: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
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

    project: Mapped[Project] = relationship(
        "Project", back_populates="clarification_sessions"
    )
    revisions: Mapped[list[GenerationRevision]] = relationship(
        "GenerationRevision",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="GenerationRevision.revision_number",
    )

    def __repr__(self) -> str:
        return (
            f"ClarificationSession(id={self.id!r}, "
            f"project_id={self.project_id!r}, status={self.status!r})"
        )


class GenerationRevision(Base):
    """Immutable snapshot of a requirement generation result version."""

    __tablename__ = "generation_revisions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("clarification_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    parent_generation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    generation_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="initial",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    project: Mapped[Project] = relationship(
        "Project", back_populates="generation_revisions"
    )
    session: Mapped[ClarificationSession | None] = relationship(
        "ClarificationSession", back_populates="revisions"
    )

    def __repr__(self) -> str:
        return (
            f"GenerationRevision(id={self.id!r}, "
            f"revision_number={self.revision_number!r}, "
            f"generation_id={self.generation_id!r})"
        )


__all__ = ["ClarificationSession", "GenerationRevision"]
