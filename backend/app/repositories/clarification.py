from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clarification import ClarificationSession, GenerationRevision


class ClarificationSessionRepository:
    """Data access repository for ClarificationSession entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: ClarificationSession) -> ClarificationSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: str) -> ClarificationSession | None:
        return self.db.execute(
            select(ClarificationSession).where(ClarificationSession.id == session_id)
        ).scalar_one_or_none()

    def get_by_project_and_id(self, project_id: str, session_id: str) -> ClarificationSession | None:
        return self.db.execute(
            select(ClarificationSession).where(
                ClarificationSession.project_id == project_id,
                ClarificationSession.id == session_id,
            )
        ).scalar_one_or_none()

    def list_by_project(self, project_id: str) -> list[ClarificationSession]:
        return list(
            self.db.execute(
                select(ClarificationSession)
                .where(ClarificationSession.project_id == project_id)
                .order_by(ClarificationSession.created_at.desc())
            ).scalars().all()
        )

    def update(self, session: ClarificationSession) -> ClarificationSession:
        self.db.commit()
        self.db.refresh(session)
        return session

    def delete(self, session: ClarificationSession) -> None:
        self.db.delete(session)
        self.db.commit()


class GenerationRevisionRepository:
    """Data access repository for GenerationRevision entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, revision: GenerationRevision) -> GenerationRevision:
        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def update(self, revision: GenerationRevision) -> GenerationRevision:
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def get_by_id(self, revision_id: str) -> GenerationRevision | None:
        return self.db.execute(
            select(GenerationRevision).where(GenerationRevision.id == revision_id)
        ).scalar_one_or_none()

    def get_by_generation_id(self, generation_id: str) -> GenerationRevision | None:
        return self.db.execute(
            select(GenerationRevision).where(GenerationRevision.generation_id == generation_id)
        ).scalar_one_or_none()

    def get_by_session_and_revision(
        self, session_id: str, revision_number: int
    ) -> GenerationRevision | None:
        return self.db.execute(
            select(GenerationRevision).where(
                GenerationRevision.session_id == session_id,
                GenerationRevision.revision_number == revision_number,
            )
        ).scalar_one_or_none()

    def list_by_session(self, session_id: str) -> list[GenerationRevision]:
        return list(
            self.db.execute(
                select(GenerationRevision)
                .where(GenerationRevision.session_id == session_id)
                .order_by(GenerationRevision.revision_number.asc())
            ).scalars().all()
        )

    def list_by_project(self, project_id: str) -> list[GenerationRevision]:
        return list(
            self.db.execute(
                select(GenerationRevision)
                .where(GenerationRevision.project_id == project_id)
                .order_by(GenerationRevision.created_at.desc())
            ).scalars().all()
        )

    def get_latest_by_session(self, session_id: str) -> GenerationRevision | None:
        return self.db.execute(
            select(GenerationRevision)
            .where(GenerationRevision.session_id == session_id)
            .order_by(GenerationRevision.revision_number.desc())
        ).scalars().first()


__all__ = ["ClarificationSessionRepository", "GenerationRevisionRepository"]
